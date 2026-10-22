// Serviços: as zonas em vista explodida, os containers, os registros e o editor das stacks de apps.
import { ORDEM_ZONAS, abrirJanela, atualizar, avisar, cartao, consultar, estadoContainer, falha, h, modulo, mudar,
  semAcao, statusDocker } from "../comum.js";
import { abrirZona, marcarZonas, resumirZonas, tirarFoco } from "../zonas.js";
import { vistaExplodida } from "../visor.js";

export async function verLogs(stack) {
  abrirJanela(`Logs de ${stack}`, h("p", { class: "fraco" }, "Carregando…"));
  const r = await consultar("servico.logs", { stack, linhas: 200 });
  if (r.ok === false) return abrirJanela(`Logs de ${stack}`, falha(r));
  abrirJanela(`Logs de ${stack}`, Object.entries(r.resultado).map(([nome, texto]) => [
    h("h3", null, nome), h("pre", { class: "log" }, texto || "(vazio)"),
  ]));
}

// --- editor das stacks de apps (stack.editar guarda uma foto antes; stack.desfazer volta) -------------

const contar = (texto, trecho) => texto.split(trecho).length - 1;

// A troca que leva o original ao editado: do primeiro ao último lugar que mudou, com linhas de
// contexto até o trecho ficar único. O arquivo chega com os segredos ocultos (***), então um trecho
// com *** não bate com o arquivo de verdade: esse fica para o terminal.
function trocaDoEditor(original, editado) {
  if (original === editado) return null;
  if (!original) return { conteudo: editado };
  const a = original.split("\n");
  const b = editado.split("\n");
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i++;
  let j = 0;
  while (j < a.length - i && j < b.length - i && a[a.length - 1 - j] === b[b.length - 1 - j]) j++;
  for (let contexto = 0; ; contexto++) {
    const ini = Math.max(0, i - contexto);
    const fim = Math.min(a.length, a.length - j + contexto);
    const de = a.slice(ini, fim).join("\n");
    if (de && contar(original, de) === 1) {
      if (de.includes("***")) return { erro: "esse trecho tem um segredo oculto (***): edite este pedaço pelo terminal" };
      const para = [...a.slice(ini, i), ...b.slice(i, b.length - j), ...a.slice(a.length - j, fim)].join("\n");
      return { trocar: [{ de, para }] };
    }
    if (ini === 0 && fim === a.length) return { erro: "não achei um trecho único para trocar: edite pelo terminal" };
  }
}

export function janelaEditor(stack) {
  const raiz = `/opt/atena/stacks/apps/${stack}`;
  const lista = h("div");
  const editor = h("div");
  const fotos = h("div");
  let aberto = null; // o arquivo no editor (relativo à pasta da stack)

  async function listar(sub) {
    lista.replaceChildren(h("p", { class: "fraco" }, "Carregando…"));
    const r = await consultar("arquivo.ler", { caminho: sub ? `${raiz}/${sub}` : raiz });
    if (r.ok === false) return lista.replaceChildren(falha(r), semAcao(r, "arquivo.ler") ?? "");
    const itens = r.resultado.itens ?? [];
    lista.replaceChildren(h("ul", { class: "lista arquivos" },
      sub && h("li", null, h("a", { href: "#servicos", onclick: (e) => { e.preventDefault(); listar(sub.replace(/\/?[^/]+$/, "")); } }, "Pasta de cima")),
      itens.map((n) => {
        const pasta = n.endsWith("/");
        const rel = (sub ? `${sub}/` : "") + n.replace(/\/$/, "");
        return h("li", null, h("a", { href: "#servicos", class: pasta ? "pasta" : null, onclick: (e) => {
          e.preventDefault();
          if (pasta) listar(rel);
          else abrir(rel);
        } }, n));
      })));
  }

  async function abrir(rel) {
    aberto = rel;
    editor.replaceChildren(h("p", { class: "fraco" }, `Abrindo ${rel}…`));
    const r = await consultar("arquivo.ler", { caminho: `${raiz}/${rel}` });
    if (r.ok === false) return editor.replaceChildren(h("h3", null, rel), falha(r));
    if (r.resultado.binario || r.resultado.cortado)
      return editor.replaceChildren(h("h3", null, rel), h("p", { class: "fraco" },
        r.resultado.binario ? "Arquivo binário: o editor só mexe em texto." : "Arquivo grande demais para o editor (mais de 64 KB)."));
    const original = r.resultado.texto;
    const area = h("textarea", { class: "codigo", rows: "18", spellcheck: "false", autocapitalize: "off" }, original);
    editor.replaceChildren(h("h3", null, rel), area,
      h("div", { class: "botoes" }, h("button", { type: "button", class: "principal", onclick: async () => {
        const troca = trocaDoEditor(original, area.value);
        if (!troca) return avisar("Nada mudou.");
        if (troca.erro) return avisar(troca.erro, "erro");
        const x = await mudar("stack.editar", { stack, arquivo: rel, ...troca });
        if (x && x.ok !== false) {
          avisar(x.resultado?.mudou === false ? "O arquivo já estava assim." : "A foto do anterior ficou guardada. Falta aplicar para valer.");
          abrir(rel);
        }
      } }, "Gravar")),
      h("p", { class: "fraco" }, "Os segredos aparecem como ***; o trecho que você muda não pode ter ***. Um compose com erro não é gravado."));
  }

  async function verFotos() {
    fotos.replaceChildren(h("p", { class: "fraco" }, "Carregando…"));
    const r = await consultar("stack.fotos", { stack });
    if (r.ok === false) return fotos.replaceChildren(falha(r));
    fotos.replaceChildren(h("h3", null, "Fotos (o arquivo antes de cada edição)"), r.resultado.fotos.length
      ? h("ul", { class: "lista" }, r.resultado.fotos.map((f) => h("li", null,
        h("div", { class: "stack-topo" },
          h("span", null, f.arquivo, h("small", null, ` ${f.quando}${f.existia ? "" : " (o arquivo não existia)"}`)),
          h("button", { type: "button", class: "discreto", onclick: async () => {
            const x = await mudar("stack.desfazer", { stack, foto: f.foto }, `Voltar ${f.arquivo} como estava antes da edição de ${f.quando}?`);
            if (x && x.ok !== false) {
              if (x.resultado?.aviso) avisar(x.resultado.aviso, "erro");
              verFotos();
              if (aberto === f.arquivo) abrir(f.arquivo);
            }
          } }, "Desfazer")))))
      : h("p", { class: "fraco" }, "Nenhuma edição guardada."));
  }

  abrirJanela(`Editar a stack ${stack}`,
    h("p", { class: "fraco" }, "Cada gravação guarda uma foto do arquivo de antes. Aplicar sobe a stack com o que está gravado. Os .env e as chaves ficam só para o terminal."),
    lista, editor,
    h("div", { class: "botoes" },
      h("button", { type: "button", onclick: () => mudar("stack.aplicar", { stack }, `Aplicar a stack ${stack}? Sobe com docker compose up -d --build.`) }, "Aplicar"),
      h("button", { type: "button", class: "discreto", onclick: verFotos }, "Fotos e desfazer")),
    fotos);
  listar("");
}

// O uso de CPU e RAM vem do docker stats, que leva uns 2 s: a tela sai com o estado dos containers e
// o último uso visto, e o de agora entra quando chegar
let consumoVisto = {};
const textoConsumo = (c) => (c ? `CPU ${c.cpu} · RAM ${c.ram}` : "");

function consumoDe(container, uso) {
  const el = h("span", { class: "consumo" }, textoConsumo(consumoVisto[container]));
  uso.then((x) => el.replaceChildren(textoConsumo(x[container])));
  return el;
}

export async function telaServicos() {
  const servicos = await consultar("status.servicos");
  if (servicos.ok === false) return [cartao("Serviços", falha(servicos))];
  const uso = consultar("status.containers").then((u) => {
    if (u.ok !== false) consumoVisto = Object.fromEntries(u.resultado.map((c) => [c.container, c]));
    return consumoVisto;
  });
  const zonas = {};
  for (const c of servicos.resultado) ((zonas[c.zona] ??= {})[c.stack] ??= []).push(c);
  const ordem = Object.keys(zonas).sort((a, b) => ORDEM_ZONAS.indexOf(a) - ORDEM_ZONAS.indexOf(b));
  const resumo = resumirZonas(servicos.resultado);
  marcarZonas(resumo);
  const desenho = modulo("Vista explodida", `${resumo.length} zonas · ${servicos.resultado.length} containers`, vistaExplodida(resumo, abrirZona));
  const foco = tirarFoco();
  if (foco) requestAnimationFrame(() => document.getElementById(`zona-${foco}`)?.scrollIntoView({ behavior: "smooth", block: "start" }));
  return [desenho, ordem.map((zona) => {
    const stacks = Object.keys(zonas[zona]).length;
    const containers = Object.values(zonas[zona]).flat().length;
    const m = modulo(`Zona ${zona}`, `${stacks} ${stacks === 1 ? "stack" : "stacks"} · ${containers} containers`,
    Object.entries(zonas[zona]).sort(([a], [b]) => a.localeCompare(b)).map(([stack, containers]) =>
      h("div", { class: "stack" },
        h("div", { class: "stack-topo" },
          h("strong", null, stack),
          h("span", { class: "botoes" },
            zona === "apps" && h("button", { type: "button", class: "discreto", onclick: () => janelaEditor(stack) }, "Editar"),
            h("button", { type: "button", class: "discreto", onclick: () => verLogs(stack) }, "Logs"),
            h("button", { type: "button", onclick: async () => {
              if (await mudar("servico.reiniciar", { stack }, `Reiniciar ${stack}?`)) atualizar();
            } }, "Reiniciar"))),
        h("ul", { class: "lista" }, containers.map((c) => h("li", null,
          estadoContainer(c), c.container !== stack && ` ${c.container} `,
          h("small", null, statusDocker(c.status, true), " ", consumoDe(c.container, uso))))),
      )));
    m.id = `zona-${zona}`;
    return m;
  })];
}
