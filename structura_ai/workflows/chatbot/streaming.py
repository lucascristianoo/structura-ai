"""
Streaming SSE do Copiloto Structura.AI (Padrão Lembry `app/workflows/chatbot/chat/streaming.py`).
Emite eventos SSE:
- `content`: chunks de texto da resposta
- `ui_mutation`: mutações imediatas de estado (troca de versão v1..vn, troca de arquivo, mudança de estilo AutoCAD/Blender, nova versão gerada)
- `done`: payload final consolidado com `active_file`, `ui_mutations` e `suggestions`.
"""

import json
from typing import AsyncGenerator, Optional
from structura_ai.workflows.chatbot.runner import run_chat_workflow


def format_sse_event(data: dict) -> str:
    """Formata um dicionário como evento Server-Sent Events (SSE)."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_chat_workflow(
    message: str,
    user_id: str = "default_user",
    session_id: str = "default_session",
    active_file_id: Optional[str] = None,
    region_country: str = "BR",
) -> AsyncGenerator[str, None]:
    """Gera stream de eventos SSE para o Frontend consumir em tempo real."""
    try:
        reply, suggestions, ui_mutations, active_file = await run_chat_workflow(
            message=message,
            user_id=user_id,
            session_id=session_id,
            active_file_id=active_file_id,
            region_country=region_country,
        )

        # Emite primeiro os eventos de mutação de UI (versão v1..vn, arquivo selecionado, estilo)
        for mutation in ui_mutations:
            yield format_sse_event(
                {
                    "type": "ui_mutation",
                    "session_id": session_id,
                    "mutation": mutation.model_dump(),
                }
            )

        # Emite os chunks de conteúdo
        chunk_size = 80
        chunk_num = 0
        for i in range(0, max(1, len(reply)), chunk_size):
            part = reply[i : i + chunk_size]
            if not part:
                continue
            chunk_num += 1
            yield format_sse_event(
                {
                    "type": "content",
                    "chunk": part,
                    "chunk_number": chunk_num,
                    "session_id": session_id,
                }
            )

        yield format_sse_event(
            {
                "type": "done",
                "session_id": session_id,
                "success": True,
                "total_chunks": chunk_num,
                "suggestions": suggestions,
                "ui_mutations": [m.model_dump() for m in ui_mutations],
                "active_file": active_file.model_dump() if active_file else None,
            }
        )
    except Exception as exc:
        yield format_sse_event(
            {
                "type": "error",
                "error": f"Erro ao processar mensagem: {exc}",
                "done": True,
                "session_id": session_id,
            }
        )
