// Paleta de comandos (Ctrl+K ou ⌘K no PC): digite para pular para uma tela ou disparar uma ação.
// Cada comando: { titulo, grupo, picto?, acao }. A lista é pedida de novo a cada abertura.
import { picto } from "./pictos.js";

const semAcento = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

export function iniciarPaleta(dialogo, obterComandos) {
  const campo = dialogo.querySelector("input");
  const lista = dialogo.querySelector("ul");
  let comandos = [];
  let visiveis = [];
  let marcado = 0;

  function desenhar() {
    const termos = semAcento(campo.value).split(/\s+/).filter(Boolean);
    visiveis = comandos.filter((c) => termos.every((t) => semAcento(`${c.titulo} ${c.grupo}`).includes(t))).slice(0, 40);
    marcado = Math.min(marcado, Math.max(0, visiveis.length - 1));
    lista.replaceChildren(...(visiveis.length ? visiveis.map((c, i) => {
      const item = document.createElement("li");
      item.id = `comando-${i}`;
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", String(i === marcado));
      if (c.picto) item.append(picto(c.picto));
      const titulo = document.createElement("span");
      titulo.className = "comando-titulo";
      titulo.textContent = c.titulo;
      const grupo = document.createElement("span");
      grupo.className = "comando-grupo";
      grupo.textContent = c.grupo;
      item.append(titulo, grupo);
      item.addEventListener("click", () => executar(i));
      item.addEventListener("mousemove", () => { if (marcado !== i) { marcado = i; marcar(); } });
      return item;
    }) : [Object.assign(document.createElement("li"), { className: "vazio", textContent: "Nenhum comando com esse nome." })]));
    campo.setAttribute("aria-activedescendant", visiveis.length ? `comando-${marcado}` : "");
  }

  function marcar() {
    for (const [i, item] of [...lista.children].entries()) item.setAttribute("aria-selected", String(i === marcado));
    lista.children[marcado]?.scrollIntoView({ block: "nearest" });
    campo.setAttribute("aria-activedescendant", `comando-${marcado}`);
  }

  function executar(i) {
    const c = visiveis[i];
    if (!c) return;
    dialogo.close();
    c.acao();
  }

  function abrir() {
    if (dialogo.open) return;
    comandos = obterComandos();
    campo.value = "";
    marcado = 0;
    desenhar();
    dialogo.showModal();
    campo.focus();
  }

  campo.addEventListener("input", () => { marcado = 0; desenhar(); });
  campo.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); marcado = Math.min(visiveis.length - 1, marcado + 1); marcar(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); marcado = Math.max(0, marcado - 1); marcar(); }
    else if (e.key === "Enter") { e.preventDefault(); executar(marcado); }
  });
  dialogo.addEventListener("click", (e) => { if (e.target === dialogo) dialogo.close(); }); // clique fora fecha
  addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (dialogo.open) dialogo.close();
      else abrir();
    }
  });
  return abrir;
}
