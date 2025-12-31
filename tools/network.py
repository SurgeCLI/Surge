# @app.command('network')
# def network(
#     url: Annotated[str | None, typer.Option('-u', '--url', help='HTTP URL to test (curl)', show_default=False)] = None,
#     host: Annotated[str | None, typer.Option('-h', '--host', help='Host/IP for ping and traceroute', show_default=False)] = None,
#     domain: Annotated[str | None, typer.Option('-d', '--domain', help='Domain for DNS lookup', show_default=False)] = None,
#     requests: Annotated[int, typer.Option('-n', '--count', help='Number of ICMP echo requests')] = 5,
#     dtype: Annotated[str, typer.Option('-t', '--type', help='DNS record type (A, AAAA, MX, TXT, etc.)')] = 'A',
#     sockets: Annotated[bool, typer.Option('--sockets', help='Show socket information (ss)')] = False,
#     no_trace: Annotated[bool, typer.Option('--no-trace', help='Skip traceroute/mtr when --host is set')] = False,
# ):
#     """
#     Flexible network diagnostics: run only what you request.
#     Provide one or more of: --host, --url, --domain, --sockets.
#     """

#     def header(title: str):
#         print(f'\n[bold]{title}[/bold]')
#         print('-' * len(title))

#     def warn(msg: str):
#         print(f'[warn] {msg}')

#     def normalize_url(u: str) -> str:
#         return u if u.startswith(('http://', 'https://')) else f'http://{u}'

#     def curl_brief(u: str) -> str:
#         fmt = 'HTTP %{http_code} | total %{time_total}s | connect %{time_connect}s | ttfb %{time_starttransfer}s\n'
#         return run_cmd(f'curl -s -o /dev/null -w "{fmt}" {u}')

#     def summarize_ping(out: str) -> str:
#         lines = out.splitlines()
#         sent = loss = avg = None
#         for ln in lines:
#             if 'packets transmitted' in ln and 'packet loss' in ln:
#                 parts = ln.replace(',', '').split()
#                 try:
#                     sent = int(parts[0])
#                     loss = parts[6]
#                 except Exception:
#                     pass
#             if 'rtt min/avg/max' in ln or 'round-trip min/avg/max' in ln:
#                 try:
#                     avg = ln.split('=')[1].split('/')[1].strip()
#                 except Exception:
#                     pass
#         bits = []

#         if sent is not None:
#             bits.append(f'sent={sent}')
#         if loss is not None:
#             bits.append(f'loss={loss}')
#         if avg is not None:
#             bits.append(f'avg_rtt_ms={avg}')

#         return ' | '.join(bits) if bits else (out.strip()[:200] if out else '')

#     def summarize_trace(out: str, max_lines: int = 12) -> str:
#         lines = [line for line in out.splitlines() if line.strip()]
#         if len(lines) <= max_lines:
#             return out
#         return '\n'.join(lines[:6] + ['...'] + lines[-6:])

#     # --- validate empty values FIRST ---
#     if host is not None and not str(host).strip():
#         warn('--host was provided but empty')
#         raise typer.Exit(code=2)
#     if url is not None and not str(url).strip():
#         warn('--url was provided but empty')
#         raise typer.Exit(code=2)
#     if domain is not None and not str(domain).strip():
#         warn('--domain was provided but empty')
#         raise typer.Exit(code=2)

#     # --- then require at least one section ---
#     if not any([host, url, domain, sockets]):
#         warn('Nothing to do. Provide at least one of: --host, --url, --domain, --sockets')
#         raise typer.Exit(code=1)

#     # ---- ping / traceroute (or mtr -r fallback) ----
#     if host:
#         header('Ping')
#         ping_out = run_cmd(f'ping -c {requests} {host}')
#         print(summarize_ping(ping_out) if ping_out else '[warn] ping not available or produced no output')

#         if not no_trace:
#             header('Traceroute')
#             trace_out = run_cmd(f'traceroute {host}') or run_cmd(f'mtr -r {host}')
#             print(summarize_trace(trace_out) if trace_out else '[warn] traceroute/mtr not available or produced no output')

#     # ---- http (curl) ----
#     if url:
#         header('HTTP (curl)')
#         u = normalize_url(url)
#         print(curl_brief(u))
#         headers = run_cmd(f'curl -s -I {u}')
#         print(headers.strip() if headers else '[warn] curl not available or produced no output')

#     # ---- dns ----
#     if domain:
#         header('DNS')
#         dns_out = run_cmd(f'dig +short {domain} {dtype}') or run_cmd(f'nslookup -type={dtype} {domain}')
#         print(dns_out.strip() if dns_out else '[warn] dig/nslookup not available or produced no output')

#     # ---- sockets (ss) ----
#     if sockets:
#         header('Sockets (ss)')
#         ss_out = run_cmd('ss -tulwn')
#         print(ss_out or '[warn] ss not available or produced no output')
