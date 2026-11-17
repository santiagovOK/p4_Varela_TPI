"""Ejecutor automatizado de suites REST Client (.http) para certificar E5.1 sobre PostgreSQL 16."""

import re
import sys
import json
import httpx
from pathlib import Path


def parse_and_run_http_file(file_path: Path) -> int:
    print(f"\n======================================================================")
    print(f"Ejecutando suite REST Client: {file_path.name}")
    print(f"======================================================================")

    content = file_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    variables: dict[str, str] = {}
    saved_responses: dict[str, dict] = {}

    # Patrones de expresiones regulares
    var_def_pattern = re.compile(r"^@([a-zA-Z0-9_]+)\s*=\s*(.*)$")
    step_name_pattern = re.compile(r"^#\s*@name\s+([a-zA-Z0-9_]+)")
    expected_status_pattern = re.compile(r"^#\s*Esperado:\s*(\d{3})")
    request_line_pattern = re.compile(r"^(GET|POST|PUT|DELETE|PATCH)\s+(\S+)")

    def resolve_placeholders(text_val: str) -> str:
        def replace_match(match):
            expr = match.group(1).strip()
            # Caso 1: step.response.body.$.path
            resp_match = re.match(r"^([a-zA-Z0-9_]+)\.response\.body\.\$\.(.+)$", expr)
            if resp_match:
                step_name, field_path = resp_match.group(1), resp_match.group(2)
                if step_name not in saved_responses:
                    raise KeyError(f"Paso '{step_name}' no encontrado en respuestas guardadas")
                curr = saved_responses[step_name]
                for part in field_path.split("."):
                    curr = curr[part]
                return str(curr)

            # Caso 2: variable
            if expr in variables:
                val = variables[expr]
                # Si el valor contiene marcadores de posición, resolver recursivamente
                if "{{" in val:
                    val = resolve_placeholders(val)
                return str(val)

            raise KeyError(f"Variable o expresión desconocida: '{expr}'")

        return re.sub(r"\{\{([^}]+)\}\}", replace_match, text_val)

    # Primera pasada: recolectar variables iniciales definidas antes de la primera petición
    # y dividir el contenido en secciones
    raw_sections = content.split("### ")
    
    # Procesar sección 0 para variables de nivel superior antes del primer ###
    sec0_lines = raw_sections[0].splitlines()
    for l in sec0_lines:
        m = var_def_pattern.match(l.strip())
        if m:
            variables[m.group(1)] = m.group(2).strip()

    total_requests = 0
    passed_requests = 0

    with httpx.Client(timeout=15.0) as client:
        for sec_idx, section in enumerate(raw_sections[1:], start=1):
            sec_lines = section.splitlines()
            if not sec_lines:
                continue
            title = sec_lines[0].strip()

            # Buscar la línea de petición HTTP en la sección
            req_idx = -1
            req_method = None
            req_url = None
            for idx, line in enumerate(sec_lines):
                # Verificar también variables declaradas en la sección antes de la petición
                if vmatch and req_idx == -1:
                    variables[vmatch.group(1)] = vmatch.group(2).strip()
                rm = request_line_pattern.match(line.strip())
                if rm:
                    req_idx = idx
                    req_method = rm.group(1)
                    req_url = rm.group(2)
                    break

            if req_idx == -1:
                # Sección sin petición HTTP (p. ej., bloque de comentarios o encabezado)
                continue

            # Buscar nombre del paso y código de estado esperado en líneas previas a la petición
            step_name = None
            expected_status = None
            for line in sec_lines[:req_idx]:
                sm = step_name_pattern.match(line.strip())
                if sm:
                    step_name = sm.group(1)
                em = expected_status_pattern.match(line.strip())
                if em:
                    expected_status = int(em.group(1))

            # Encabezados y cuerpo
            headers = {}
            body_lines = []
            parsing_body = False
            trailing_lines = []

            for line in sec_lines[req_idx + 1:]:
                stripped = line.strip()
                if not parsing_body:
                    if not stripped:
                        parsing_body = True
                        continue
                    if ":" in line:
                        h_k, h_v = line.split(":", 1)
                        headers[h_k.strip()] = h_v.strip()
                else:
                    # Ignorar comentarios posteriores a la petición
                    if stripped.startswith("#") or stripped.startswith("//"):
                        continue
                    # Verificar si terminó el cuerpo o si hay una asignación de variable posterior
                    v_match = var_def_pattern.match(stripped)
                    if v_match:
                        trailing_lines.append(stripped)
                    elif req_method not in ("GET", "DELETE"):
                        body_lines.append(line)
            raw_body = "\n".join(body_lines).strip()

            # Resolver marcadores de posición en URL, encabezados y cuerpo
            resolved_url = resolve_placeholders(req_url)
            resolved_headers = {k: resolve_placeholders(v) for k, v in headers.items()}
            
            resolved_body = None
            if raw_body:
                resolved_body_str = resolve_placeholders(raw_body)
                try:
                    resolved_body = json.loads(resolved_body_str)
                except Exception as e:
                    print(f"[ERROR] Error parseando JSON body en '{title}': {e}\nBody:\n{resolved_body_str}")
                    return 1

            total_requests += 1

            # Ejecutar petición HTTP
            try:
                if resolved_body is not None:
                    resp = client.request(
                        method=req_method,
                        url=resolved_url,
                        headers=resolved_headers,
                        json=resolved_body,
                    )
                else:
                    resp = client.request(
                        method=req_method,
                        url=resolved_url,
                        headers=resolved_headers,
                    )
            except Exception as e:
                print(f"[FAIL] {title} -> Error de conexión: {e}")
                return 1

            actual_status = resp.status_code
            status_ok = (expected_status is None) or (actual_status == expected_status)

            if not status_ok:
                print(f"[FAIL] {title}")
                print(f"       {req_method} {resolved_url}")
                print(f"       Esperado: {expected_status}, Recibido: {actual_status}")
                print(f"       Respuesta: {resp.text}")
                return 1

            # Guardar cuerpo de respuesta si el paso tiene un nombre asignado
            resp_json = None
            if resp.content:
                try:
                    resp_json = resp.json()
                except Exception:
                    resp_json = {"raw": resp.text}
            else:
                resp_json = {}

            if step_name:
                saved_responses[step_name] = resp_json

            # Resolver asignaciones de variables posteriores a la respuesta
            for tvar in trailing_lines:
                tvm = var_def_pattern.match(tvar)
                if tvm:
                    v_name = tvm.group(1)
                    v_val = resolve_placeholders(tvm.group(2).strip())
                    variables[v_name] = v_val

            passed_requests += 1
            exp_str = f" [Esperado: {expected_status}]" if expected_status else ""
            print(f"  [OK] {req_method} {resolved_url} -> {actual_status}{exp_str} ({title})")

    print(f"\nResultado {file_path.name}: {passed_requests}/{total_requests} peticiones verificadas con éxito.")
    return 0


def main():
    backend_tests_dir = Path(__file__).parent
    relaciones_path = backend_tests_dir / "relaciones.http"
    productos_path = backend_tests_dir / "productos.http"

    ret1 = parse_and_run_http_file(relaciones_path)
    if ret1 != 0:
        sys.exit(ret1)

    ret2 = parse_and_run_http_file(productos_path)
    if ret2 != 0:
        sys.exit(ret2)

    print("\n======================================================================")
    print("TODAS LAS SUITES REST CLIENT EJECUTADAS Y CERTIFICADAS EXITOSAMENTE!")
    print("======================================================================")
    sys.exit(0)


if __name__ == "__main__":
    main()
