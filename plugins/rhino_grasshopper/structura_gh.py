"""
Structura.AI Bridge — Rhinoceros / Grasshopper GhPython Component
Componente paramétrico para avaliação física contínua durante a modelagem algorítmica.

Entradas no Grasshopper:
    Run (bool): Booleano para disparar a sincronização
    ServerURL (str): Endereço do Structura.AI (ex: "http://localhost:8000")
    SpanMeters (float): Comprimento do vão crítico gerado no Grasshopper
    BeamWidthCM (float): Largura estimada da viga (padrão: 20cm)
    BeamHeightCM (float): Altura estimada da viga (padrão: 30cm)
    fck (float): Resistência do concreto (padrão: 30 MPa)

Saídas do Grasshopper:
    IsFeasible (bool): True se atende a NBR 6118, False se reprovado
    DeflectionMM (float): Flecha elástica total calculada em mm
    LimitMM (float): Limite normativo L/250
    Status (str): Mensagem resumida
    StudioURL (str): Link para abrir o laudo e as 5 propostas de redesign
    RedesignVariants (list): Resumo das 5 alternativas geradas
"""
import json
try:
    import urllib.request as urllib_request
except ImportError:
    import urllib2 as urllib_request  # Compatibilidade com IronPython 2.7 do Rhino clássico


def evaluate_structura(server_url, span_m, bw_cm, bh_cm, fck_mpa):
    url = (server_url or "http://localhost:8000").rstrip("/") + "/api/plugins/sync"
    payload = {
        "project_name": "Rhinoceros Grasshopper Parametric Study",
        "source_software": "Rhino Grasshopper",
        "span_meters": float(span_m or 8.0),
        "beam_width_cm": float(bw_cm or 20.0),
        "beam_height_cm": float(bh_cm or 30.0),
        "fck_mpa": float(fck_mpa or 30.0),
        "cantilever_meters": 0.0,
        "dead_load_kn_m": 22.0,
        "live_load_kn_m": 3.0,
    }

    req = urllib_request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Grasshopper-StructuraAI/2.0"},
    )
    with urllib_request.urlopen(req, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


# Execução do componente Grasshopper
if "Run" in globals() and Run:
    try:
        res = evaluate_structura(
            ServerURL if "ServerURL" in globals() else "http://localhost:8000",
            SpanMeters if "SpanMeters" in globals() else 10.0,
            BeamWidthCM if "BeamWidthCM" in globals() else 20.0,
            BeamHeightCM if "BeamHeightCM" in globals() else 28.0,
            fck if "fck" in globals() else 30.0,
        )
        diag = res.get("deterministic_diagnosis", {})
        IsFeasible = diag.get("is_feasible", True)
        DeflectionMM = diag.get("calculated_deflection_mm", 0.0)
        LimitMM = diag.get("normative_limit_mm", 0.0)
        Status = "APROVADO (NBR 6118)" if IsFeasible else f"REPROVADO: Flecha {DeflectionMM:.1f}mm > {LimitMM:.1f}mm"
        StudioURL = res.get("studio_url", "")
        RedesignVariants = [v.get("variant_name") for v in res.get("redesign_variants", [])]
    except Exception as e:
        IsFeasible = False
        DeflectionMM = -1.0
        LimitMM = -1.0
        Status = f"Erro na ponte Structura.AI: {e}"
        StudioURL = ""
        RedesignVariants = []
else:
    Status = "Conecte 'Run' = True para avaliar estrutura"
    IsFeasible = True
    DeflectionMM = 0.0
    LimitMM = 0.0
    StudioURL = ""
    RedesignVariants = []
