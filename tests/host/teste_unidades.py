"""As unidades do systemd do repositório passam no systemd-analyze verify: chave desconhecida, valor que não
vale, dependência que falta. Elas vão para uma pasta própria (preenchidas com o atena.conf.example), achadas
pelo SYSTEMD_UNIT_PATH junto com as do sistema, e os comandos delas apontam para executáveis de mentira
(no CI, os de verdade não existem). Uma linha da saída que cite uma unidade nossa é uma falha; o que o
systemd diz das unidades dele mesmo fica de fora."""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(RAIZ, "install"))
import estado  # noqa: E402

FALHAS = []


def confere(nome, condicao, extra=""):
    print(("OK    " if condicao else "FALHA ") + nome + (f"  [{extra}]" if extra and not condicao else ""))
    if not condicao:
        FALHAS.append(nome)


analyze = shutil.which("systemd-analyze")
confere("há o systemd-analyze (no CI, o pacote systemd)", analyze is not None)
if analyze:
    tmp = tempfile.mkdtemp(prefix="teste-unidades-")
    pasta, binarios = f"{tmp}/unidades", f"{tmp}/bin"
    os.makedirs(binarios)
    conf = estado.ler_conf(os.path.join(RAIZ, "atena.conf.example"))
    origem = os.path.join(RAIZ, "host", "systemd")
    for rel in estado.arquivos(RAIZ, "host/systemd"):
        texto = open(os.path.join(RAIZ, rel), "rb").read()
        if estado.e_modelo(texto):
            texto = estado.renderizar(texto, conf, rel)
        texto = texto.replace(b"/usr/local/sbin/", f"{binarios}/".encode())
        destino = os.path.join(pasta, os.path.relpath(os.path.join(RAIZ, rel), origem))
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        open(destino, "wb").write(texto)
    comandos = set(re.findall(rf"{re.escape(binarios)}/([\w.@-]+)",
                              "".join(open(f).read() for f in glob.glob(f"{pasta}/**/*", recursive=True) if os.path.isfile(f))))
    for c in comandos:
        open(f"{binarios}/{c}", "w").write("#!/bin/sh\n")
        os.chmod(f"{binarios}/{c}", 0o755)
    confere("os comandos das unidades existem no repositório (host/sbin)",
            all(os.path.isfile(os.path.join(RAIZ, "host", "sbin", c)) for c in comandos),
            sorted(c for c in comandos if not os.path.isfile(os.path.join(RAIZ, "host", "sbin", c))))
    # o que as unidades pedem e pode não existir onde o teste roda (num container, não há Docker)
    for externa in ("docker.service", "tailscaled.service"):
        if not any(os.path.exists(f"{d}/{externa}") for d in ("/etc/systemd/system", "/usr/lib/systemd/system", "/lib/systemd/system")):
            open(f"{pasta}/{externa}", "w").write("[Service]\nExecStart=/bin/true\n")
    unidades = sorted(os.path.basename(f) for f in glob.glob(f"{pasta}/*") if os.path.isfile(f) and "@." not in f
                      and f.endswith((".service", ".timer", ".path", ".socket", ".slice"))
                      and os.path.basename(f).startswith("atena"))
    # os modelos (@) com uma instância de exemplo
    unidades += [os.path.basename(f).replace("@.", "@exemplo.") for f in glob.glob(f"{pasta}/*@.service")]
    r = subprocess.run([analyze, "verify", "--man=no", *unidades], cwd=pasta, capture_output=True, text=True,
                       env=dict(os.environ, SYSTEMD_UNIT_PATH=f"{pasta}:"), timeout=120)
    nossas = [linha for linha in (r.stdout + r.stderr).split("\n")
              if pasta in linha or re.search(r"\batena[\w@.-]*\.(service|timer|path|socket|slice)\b", linha)]
    confere(f"systemd-analyze verify: as {len(unidades)} unidades da Atena sem erro nem aviso", not nossas, nossas)
    confere("e há o que conferir (os serviços, os timers, as fatias e os modelos)",
            len(unidades) >= 20 and any("@exemplo" in u for u in unidades), unidades)

    # o teste pega o erro: uma chave desconhecida numa unidade nossa
    errada = f"{pasta}/atena-vigia.service"
    open(errada, "a").write("Restar=always\n")
    r = subprocess.run([analyze, "verify", "--man=no", "atena-vigia.service"], cwd=pasta, capture_output=True,
                       text=True, env=dict(os.environ, SYSTEMD_UNIT_PATH=f"{pasta}:"), timeout=60)
    confere("e acusa uma chave escrita errado (Restar=)", "Restar" in r.stdout + r.stderr, r.stdout + r.stderr)
    shutil.rmtree(tmp)

print(f"\n{len(FALHAS)} falhas" + (": " + ", ".join(FALHAS) if FALHAS else ""))
sys.exit(1 if FALHAS else 0)
