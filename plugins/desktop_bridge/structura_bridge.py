#!/usr/bin/env python3
"""
Structura.AI — Desktop Hot-Folder Bridge
Monitora uma pasta local para upload automático de arquivos CAD/BIM (.dxf, .ifc, .obj)
exportados por AutoCAD, Revit, Archicad ou SketchUp.
"""
import os
import sys
import time
from pathlib import Path
import urllib.request
import urllib.error
import mimetypes
import webbrowser

SUPPORTED_EXTS = {".dxf", ".ifc", ".obj", ".gltf", ".glb", ".png", ".jpg", ".pdf"}


def upload_to_structura(file_path: Path, server_url: str = "http://localhost:8000"):
    print(f"\n📤 Novo projeto detectado: {file_path.name}")
    print(f"⏳ Enviando para {server_url}...")

    boundary = "----StructuraBoundary7MA4YWxkTrZu0gW"
    data = bytearray()

    # Adicionar campo title
    data.extend(f"--{boundary}\r\n".encode("utf-8"))
    data.extend(b'Content-Disposition: form-data; name="title"\r\n\r\n')
    data.extend(f"Projeto {file_path.stem}\r\n".encode("utf-8"))

    # Adicionar arquivo
    mime = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    data.extend(f"--{boundary}\r\n".encode("utf-8"))
    data.extend(f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode("utf-8"))
    data.extend(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
    with open(file_path, "rb") as f:
        data.extend(f.read())
    data.extend(b"\r\n")
    data.extend(f"--{boundary}--\r\n".encode("utf-8"))

    endpoint = f"{server_url.rstrip('/')}/api/projects/upload"
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "StructuraDesktopBridge/2.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            import json
            res = json.loads(resp.read().decode("utf-8"))
            project_id = res.get("project_id")
            url = f"{server_url.rstrip('/')}/projects/{project_id}"
            print(f"✅ Projeto processado com sucesso!")
            print(f"👉 Abrindo laudo e alternativas no navegador: {url}")
            webbrowser.open(url)
    except Exception as e:
        print(f"❌ Falha no envio: {e}")


def watch_folder(folder_path: Path, server_url: str = "http://localhost:8000"):
    folder_path.mkdir(parents=True, exist_ok=True)
    print("=" * 60)
    print(f"  🏛️ Structura.AI Desktop Hot-Folder Bridge Ativa")
    print(f"  📂 Pasta monitorada: {folder_path.resolve()}")
    print(f"  ⚡ Servidor: {server_url}")
    print(f"  Formatos vigiados: {', '.join(sorted(SUPPORTED_EXTS))}")
    print("=" * 60)
    print("Dica: Salve ou exporte seus arquivos do Revit/AutoCAD aqui dentro!")

    seen_files = set(folder_path.iterdir())

    while True:
        try:
            time.sleep(1.5)
            current_files = set(folder_path.iterdir())
            new_files = current_files - seen_files
            for nf in new_files:
                if nf.is_file() and nf.suffix.lower() in SUPPORTED_EXTS:
                    # Aguarda fim de escrita pelo CAD
                    time.sleep(0.5)
                    upload_to_structura(nf, server_url)
            seen_files = current_files
        except KeyboardInterrupt:
            print("\n👋 Bridge encerrada.")
            break
        except Exception as e:
            print(f"Alerta: {e}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "StructuraSync"
    srv = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    watch_folder(target, srv)
