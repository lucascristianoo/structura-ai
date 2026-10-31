#!/usr/bin/env python3
"""
Automated MVP Demo Screen Recorder for Structura.AI.
Controls Brave headless via Chrome DevTools Protocol (CDP) to execute the complete
essential workflow, capturing 1080p frames and compiling them into MP4 using ffmpeg.
"""
import asyncio
import base64
import glob
import json
import os
import shutil
import subprocess
import time
import httpx
import websockets

FRAME_DIR = "/home/lucas_cristiano/Vídeos/demo_frames"
OUTPUT_VIDEO = "/home/lucas_cristiano/Vídeos/DEMO_STRUCTURA_AI_MVP_OFICIAL.mp4"
SAMPLE_DXF = "/home/lucas_cristiano/Programacao/structura-ai/tests/samples/dxf/portal_frame_meters.dxf"

os.makedirs(FRAME_DIR, exist_ok=True)
for f in glob.glob(f"{FRAME_DIR}/*.png"):
    try:
        os.remove(f)
    except Exception:
        pass

frame_count = 0

async def send_cmd(ws, msg_id, method, params=None):
    payload = {"id": msg_id, "method": method}
    if params:
        payload["params"] = params
    await ws.send(json.dumps(payload))
    while True:
        raw = await ws.recv()
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data

async def eval_js(ws, msg_id, expression, await_promise=False):
    params = {"expression": expression, "returnByValue": True, "awaitPromise": await_promise}
    res = await send_cmd(ws, msg_id, "Runtime.evaluate", params)
    return res.get("result", {}).get("result", {}).get("value")

async def record_frame(ws, msg_id_holder, repeat=1, delay=0.15):
    global frame_count
    msg_id_holder[0] += 1
    res = await send_cmd(ws, msg_id_holder[0], "Page.captureScreenshot", {"format": "png"})
    raw_data = base64.b64decode(res["result"]["data"])
    for _ in range(repeat):
        frame_count += 1
        filepath = f"{FRAME_DIR}/frame_{frame_count:05d}.png"
        with open(filepath, "wb") as f:
            f.write(raw_data)
    if delay > 0:
        await asyncio.sleep(delay)

async def main():
    print(">>> 1. Iniciando navegador headless Brave com porta CDP 9222...")
    user_data = "/tmp/brave_demo_session_clean"
    shutil.rmtree(user_data, ignore_errors=True)
    os.makedirs(user_data, exist_ok=True)

    browser_proc = subprocess.Popen([
        "/opt/brave.com/brave/brave",
        "--headless=new",
        "--remote-debugging-port=9222",
        f"--user-data-dir={user_data}",
        "--window-size=1920,1080",
        "--hide-scrollbars",
        "--disable-gpu-sandbox",
        "--no-sandbox",
        "http://localhost:8000"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        time.sleep(3.0)
        tabs_res = httpx.get("http://localhost:9222/json/list", timeout=5.0)
        tabs = tabs_res.json()
        target_tab = None
        for t in tabs:
            if t.get("type") == "page":
                target_tab = t
                break
        if not target_tab:
            raise RuntimeError("Nenhuma aba ativa encontrada no Brave!")

        ws_url = target_tab["webSocketDebuggerUrl"]
        print(f">>> 2. Conectado via CDP na aba: {target_tab.get('title')}")

        msg_id = [100]

        async with websockets.connect(ws_url, max_size=20_000_000) as ws:
            await send_cmd(ws, msg_id[0], "Emulation.setDeviceMetricsOverride", {
                "width": 1920,
                "height": 1080,
                "deviceScaleFactor": 1,
                "mobile": False
            })

            # Passo 1: Tela de Login
            print(">>> 3. Capturando tela de login inicial...")
            await asyncio.sleep(1.0)
            await record_frame(ws, msg_id, repeat=6, delay=0.15)

            # Login como Lucas Cristiano
            print(">>> 4. Realizando login como Lucas Cristiano (Arquiteto)...")
            await eval_js(ws, msg_id[0], """
                const input = document.getElementById('login-username-input');
                if (input) {
                    input.value = 'Lucas Cristiano (Arquiteto)';
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
                const btn = document.querySelector('#fake-login-form button[type="submit"]');
                if (btn) btn.click();
            """)
            await asyncio.sleep(1.2)
            await record_frame(ws, msg_id, repeat=8, delay=0.15)

            # Passo 2: Modal de Chaves API
            print(">>> 5. Demonstrando Modal de Chaves API (Botão de Engrenagem)...")
            await eval_js(ws, msg_id[0], """
                const btn = document.getElementById('api-settings-btn');
                if (btn) btn.click();
            """)
            await asyncio.sleep(1.0)
            await record_frame(ws, msg_id, repeat=12, delay=0.15)

            # Fechando modal de chaves
            print(">>> 6. Fechando modal de chaves...")
            await eval_js(ws, msg_id[0], """
                const closeBtn = document.getElementById('api-settings-close-btn');
                if (closeBtn) closeBtn.click();
            """)
            await asyncio.sleep(0.8)
            await record_frame(ws, msg_id, repeat=5, delay=0.15)

            # Passo 3: Upload do Arquivo CAD DXF
            print(">>> 7. Upload do projeto DXF real (portal_frame_meters.dxf)...")
            with open(SAMPLE_DXF, "rb") as f:
                dxf_b64 = base64.b64encode(f.read()).decode("utf-8")

            js_drop = f"""
                const bin = atob("{dxf_b64}");
                const u8 = new Uint8Array(bin.length);
                for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
                const f = new File([u8], "portal_frame_meters.dxf", {{ type: "application/dxf" }});
                const dt = new DataTransfer();
                dt.items.add(f);
                const dropzone = document.getElementById("file-dropzone");
                dropzone.dispatchEvent(new DragEvent("drop", {{ dataTransfer: dt, bubbles: true }}));
            """
            await eval_js(ws, msg_id[0], js_drop)
            await asyncio.sleep(3.5)
            await record_frame(ws, msg_id, repeat=14, delay=0.15)

            # Passo 4: Órbita 3D em Three.js
            print(">>> 8. Orbitando o modelo 3D em Three.js...")
            for step in range(24):
                angle = step * (3.14159 * 2 / 24)
                await eval_js(ws, msg_id[0], f"""
                    if (window.viewport && window.viewport.camera) {{
                        const dist = 16.0;
                        window.viewport.camera.position.x = Math.sin({angle}) * dist;
                        window.viewport.camera.position.z = Math.cos({angle}) * dist;
                        window.viewport.camera.position.y = 8.0;
                        window.viewport.camera.lookAt(0, 3, 0);
                        if (window.viewport.controls) window.viewport.controls.update();
                    }}
                """)
                await record_frame(ws, msg_id, repeat=2, delay=0.08)

            # Passo 5: Alternando para vista 2D (Planta Baixa)
            print(">>> 9. Alternando para vista 2D (Planta Baixa & Corte Estrutural)...")
            await eval_js(ws, msg_id[0], """
                const btn2d = document.querySelector('[data-view-dim="2d"]');
                if (btn2d) btn2d.click();
            """)
            await asyncio.sleep(1.8)
            await record_frame(ws, msg_id, repeat=14, delay=0.15)

            # Retornando para 3D
            print(">>> 10. Retornando ao 3D e acionando Chat Copiloto...")
            await eval_js(ws, msg_id[0], """
                const btn3d = document.querySelector('[data-view-dim="3d"]');
                if (btn3d) btn3d.click();
            """)
            await asyncio.sleep(1.0)
            await record_frame(ws, msg_id, repeat=6, delay=0.15)

            # Passo 6: Debate no Chat Copiloto via Sugestão Rápida ICP
            print(">>> 11. Clicando em sugestão rápida de consultoria estrutural no Chat...")
            await eval_js(ws, msg_id[0], """
                const btns = document.querySelectorAll("#chat-suggestions-bar button");
                if (btns.length > 1) btns[1].click();
                else if (btns.length > 0) btns[0].click();
            """)
            await asyncio.sleep(4.0)
            await eval_js(ws, msg_id[0], """
                const box = document.getElementById('copilot-chat-box');
                if (box) box.scrollTop = box.scrollHeight;
            """)
            await record_frame(ws, msg_id, repeat=18, delay=0.15)

            # Passo 7: Conversão de Formato para Blender 3D (Versão v2)
            print(">>> 12. Convertendo formato para Blender 3D (gerando versão v2)...")
            await eval_js(ws, msg_id[0], """
                const sel = document.getElementById('software-format-select');
                if (sel) {
                    sel.value = 'blender';
                    sel.dispatchEvent(new Event('change', { bubbles: true }));
                }
                const btn = document.getElementById('btn-convert-format');
                if (btn) btn.click();
            """)
            await asyncio.sleep(3.5)
            await record_frame(ws, msg_id, repeat=14, delay=0.15)

            # Passo 8: Botões de Exportação
            print(">>> 13. Exibindo conclusão e botões de exportação (IFC, DXF, Laudo)...")
            await record_frame(ws, msg_id, repeat=14, delay=0.15)

    finally:
        browser_proc.terminate()
        shutil.rmtree(user_data, ignore_errors=True)

    print(f">>> 14. Total de frames capturados: {frame_count}. Compilando MP4 1080p final...")
    os.makedirs(os.path.dirname(OUTPUT_VIDEO), exist_ok=True)
    ffmpeg_cmd = [
        "flatpak", "run", "--command=ffmpeg", "com.obsproject.Studio",
        "-y",
        "-framerate", "6",
        "-i", f"{FRAME_DIR}/frame_%05d.png",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "19",
        "-preset", "veryfast",
        "-movflags", "+faststart",
        OUTPUT_VIDEO
    ]
    subprocess.run(ffmpeg_cmd, check=True)
    size_mb = os.path.getsize(OUTPUT_VIDEO) / (1024 * 1024)
    print(f">>> SUCESSO ABSOLUTO! Vídeo gerado: {OUTPUT_VIDEO} ({size_mb:.2f} MB)")

if __name__ == "__main__":
    asyncio.run(main())
