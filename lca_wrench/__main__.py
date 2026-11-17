"""Start LCA Wrench on this computer and open it in the browser: `python -m lca_wrench`.

Works the same on macOS, Linux and Windows. The server listens on 127.0.0.1 only (one local user).
"""

from __future__ import annotations

import argparse
import os
import socket
import threading
import webbrowser

from . import __version__


def _listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m lca_wrench", description="LCA Wrench: local web UI for Brightway 2.5.")
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8787)), help="port on 127.0.0.1 (default 8787)")
    p.add_argument("--no-browser", action="store_true", help="do not open the browser")
    p.add_argument("--version", action="version", version=f"LCA Wrench {__version__}")
    args = p.parse_args(argv)
    url = f"http://127.0.0.1:{args.port}"
    if _listening(args.port):
        print(f"Port {args.port} is in use; LCA Wrench may already be running: {url}")
        if not args.no_browser:
            webbrowser.open(url)
        return 0
    # bw2calc warns about an optional solver and about empty methods; both are harmless here
    os.environ.setdefault("PYTHONWARNINGS", "ignore::UserWarning:bw2calc,ignore::UserWarning:bw2calc.lca")
    import warnings

    warnings.filterwarnings("ignore", category=UserWarning, module="bw2calc")
    import uvicorn

    print(f"LCA Wrench {__version__} starts on {url}")
    print("The first build takes a few seconds. Stop with Ctrl+C.")
    if not args.no_browser:
        def _open() -> None:
            import time

            for _ in range(240):
                if _listening(args.port):
                    webbrowser.open(url)
                    return
                time.sleep(0.5)

        threading.Thread(target=_open, daemon=True).start()
    uvicorn.run("lca_wrench.api:app", host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
