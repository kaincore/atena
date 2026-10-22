// Sistema: sensores, processos, rede e o registro do systemd.
import { botaoAtualizar, campo, cartao, consultar, falha, gb, h, item, itens, linha, medidor, modulo, num, semAcao } from "../comum.js";
import { visorSistema } from "../visor.js";

function grau(rotulo, c, quente) {
  if (c == null) return linha(rotulo, "sem leitura");
  return [linha(rotulo, `${num(c, 1)} °C`), medidor(c / quente, 1)];
}

async function cartaoSensores() {
  const r = await consultar("sistema.sensores");
  const c = r.ok === false ? cartao("Sensores", falha(r), semAcao(r, "sistema.sensores")) : (() => {
    const s = r.resultado;
    const placa = s.placa ?? {};
    const m = modulo("Sensores", s.avaliacao,
      visorSistema(s),
      linha("Avaliação", h("span", { class: `selo ${s.avaliacao === "normal" ? "ok" : "ruim"}` }, s.avaliacao)),
      grau("CPU", s.cpu.temperatura_c, s.cpu.quente_a_partir_de_c),
      s.cpu.nucleos_c && linha("Núcleos", Object.entries(s.cpu.nucleos_c).map(([n, t]) => `${n} ${num(t, 1)} °C`).join(" · ")),
      grau("NVMe", s.nvme.temperatura_c, s.nvme.alerta_c),
      s.gpu && [grau("GPU", s.gpu.temperatura_c, s.gpu.quente_a_partir_de_c),
        linha("GPU agora", [s.gpu.uso_pct != null && `uso ${num(s.gpu.uso_pct)}%`, s.gpu.consumo_w != null && `${num(s.gpu.consumo_w, 1)} W`,
          s.gpu.ventoinha_pct != null && `ventoinha ${num(s.gpu.ventoinha_pct)}%`].filter(Boolean).join(" · ") || "sem leitura")],
      Object.entries(placa.ventoinhas_rpm ?? {}).map(([f, rpm]) => linha(`Ventoinha ${f}`, `${num(rpm)} RPM`)),
      placa.temperaturas_c && h("details", null, h("summary", null, "Sensores da placa"),
        Object.entries(placa.temperaturas_c).map(([n, t]) => linha(n, `${num(t, 1)} °C`))),
      placa.obs && h("p", { class: "fraco" }, placa.obs),
      s.cpu.quente_a_partir_de_c && h("p", { class: "fraco" }, `As barras enchem até o ponto de alerta (CPU ${s.cpu.quente_a_partir_de_c} °C).`));
    m.classList.add("largo");
    return m;
  })();
  c.append(botaoAtualizar(async () => c.replaceWith(await cartaoSensores())));
  return c;
}

// "1-21:19:42" (dias-horas:min:seg, como o ps mostra) em "1 d 21 h"
function duracao(etime) {
  const [dias, resto] = etime.includes("-") ? etime.split("-") : ["0", etime];
  const [s = 0, m = 0, hr = 0] = resto.split(":").reverse().map(Number);
  if (+dias) return `${+dias} d ${hr} h`;
  if (hr) return `${hr} h ${m} min`;
  return m ? `${m} min` : `${s} s`;
}

const tamanho = (kb) => (kb >= 1024 * 1024 ? gb(kb / 1024) : `${num(Math.round(kb / 1024))} MB`);

// a saída do ps: PID USER %CPU %MEM RSS ELAPSED COMMAND
function lerProcessos(texto) {
  return texto.split("\n").slice(1).filter((l) => l.trim()).map((l) => {
    const [pid, usuario, cpu, mem, rss, tempo, ...comando] = l.trim().split(/\s+/);
    return { pid, usuario, cpu, mem, rss: Number(rss), tempo, comando: comando.join(" ") };
  });
}

const processosOrdem = { ordem: "cpu" };

async function cartaoProcessos() {
  const r = await consultar("sistema.processos", { ordem: processosOrdem.ordem, quantos: 25 });
  const refazer = async () => c.replaceWith(await cartaoProcessos());
  const escolha = h("div", { class: "filtros" }, campo("Mais usam", h("select", { onchange: (evento) => {
    processosOrdem.ordem = evento.target.value;
    refazer();
  } }, [["cpu", "CPU"], ["ram", "RAM"]].map(([v, t]) => h("option", { value: v, selected: v === processosOrdem.ordem }, t)))));
  const c = r.ok === false ? cartao("Processos", falha(r), semAcao(r, "sistema.processos")) : cartao("Processos", escolha,
    itens(lerProcessos(r.resultado).map((p) => item({
      classe: "processo",
      nome: h("div", { class: "comando", title: p.comando, onclick: (evento) => evento.currentTarget.classList.toggle("aberto") }, p.comando),
      detalhe: `${p.usuario} · CPU ${num(Number(p.cpu), 1)}% · RAM ${tamanho(p.rss)} · pid ${p.pid} · há ${duracao(p.tempo)}`,
    }))),
    h("p", { class: "fraco" }, "A CPU é a média desde que o processo começou (é assim que o ps mede). Toque no comando para ver inteiro."));
  c.append(botaoAtualizar(refazer));
  return c;
}

// --- rede: o ip -br addr e o ss -tuln do servidor ---

function tipoInterface(nome) {
  if (nome === "lo") return "só o servidor";
  if (nome.startsWith("tailscale")) return "Tailscale";
  if (/^(br-|docker|veth)/.test(nome)) return "containers";
  return "rede de casa";
}

function lerInterfaces(texto) {
  return texto.split("\n").filter((l) => l.trim()).map((l) => {
    const [nome, estado, ...enderecos] = l.trim().split(/\s+/);
    return { nome: nome.split("@")[0], estado, enderecos: enderecos.map((e) => e.split("/")[0]) };
  });
}

// "100.64.0.1%tailscale0:3000", "[::1]:323", "*:5353" → onde a porta está aberta
function lerPortas(texto, interfaces) {
  const deQuem = new Map(interfaces.flatMap((i) => i.enderecos.map((e) => [e, i.nome])));
  const portas = new Map();
  for (const l of texto.split("\n")) {
    const [proto, , , , local] = l.trim().split(/\s+/);
    if (!local) continue;
    const corte = local.lastIndexOf(":");
    const [endereco, iface] = local.slice(0, corte).replace(/[[\]]/g, "").split("%");
    const porta = Number(local.slice(corte + 1));
    const alcance = iface ? tipoInterface(iface)
      : ["0.0.0.0", "::", "*"].includes(endereco) ? "todas as redes"
      : /^127\.|^::1$/.test(endereco) ? "só o servidor"
      : deQuem.has(endereco) ? tipoInterface(deQuem.get(endereco)) : endereco;
    const chave = `${porta}/${proto}`;
    if (!portas.has(chave)) portas.set(chave, { porta, proto, alcances: new Set(), enderecos: new Set() });
    portas.get(chave).alcances.add(alcance);
    portas.get(chave).enderecos.add(endereco);
  }
  return [...portas.values()].sort((a, b) => a.porta - b.porta || a.proto.localeCompare(b.proto));
}

async function cartaoRede() {
  const r = await consultar("sistema.rede");
  const c = r.ok === false ? cartao("Rede", falha(r), semAcao(r, "sistema.rede")) : (() => {
    const interfaces = lerInterfaces(r.resultado.enderecos);
    const visiveis = interfaces.filter((i) => !i.nome.startsWith("veth"));
    const portas = lerPortas(r.resultado.portas, interfaces);
    return cartao("Rede",
      h("h3", null, "Endereços"),
      itens(visiveis.map((i) => item({
        led: i.estado === "DOWN" ? "apagado" : "ok",
        nome: [h("strong", null, i.nome), h("small", null, ` ${tipoInterface(i.nome)}`)],
        detalhe: [i.estado === "DOWN" && "desligada", ...i.enderecos.filter((e) => !e.startsWith("fe80:"))].filter(Boolean).join(" · ") || "sem endereço",
      }))),
      interfaces.length > visiveis.length && h("p", { class: "fraco" }, `Mais ${interfaces.length - visiveis.length} interfaces veth, uma por container.`),
      h("h3", null, `Portas abertas (${portas.length})`),
      itens(portas.map((p) => item({
        nome: [h("strong", null, `${p.porta}`), h("small", null, ` ${p.proto}`),
          [...p.alcances].map((a) => h("span", { class: `selo ${a === "todas as redes" ? "ruim" : "neutro"}` }, a))],
        detalhe: [...p.enderecos].join(" · "),
      }))),
      h("p", { class: "fraco" }, "Aberta aqui não quer dizer aberta lá fora: o firewall (ufw) ainda filtra o que chega."));
  })();
  c.append(botaoAtualizar(async () => c.replaceWith(await cartaoRede())));
  return c;
}

// --- registro do systemd (journalctl) ---

const registro = { unidade: "", prioridade: "err", desde: "6h", linhas: 100 };
const UNIDADES_COMUNS = ["atena-executor.service", "docker.service", "containerd.service", "ssh.service", "tailscaled.service", "ufw.service"];
let unidadesVistas = null;

async function cartaoRegistro() {
  const [r, sistema] = await Promise.all([
    consultar("servico.journal", {
      linhas: registro.linhas, ...(registro.unidade ? { unidade: registro.unidade } : {}),
      ...(registro.prioridade ? { prioridade: registro.prioridade } : {}), ...(registro.desde ? { desde: registro.desde } : {}),
    }),
    unidadesVistas ? null : consultar("status.sistema"),
  ]);
  if (sistema && sistema.ok !== false) unidadesVistas = sistema.resultado.unidades.map((u) => u.nome);
  const opcoes = (nome, lista) => h("select", { name: nome }, lista.map(([v, t]) =>
    h("option", { value: String(v), selected: String(v) === String(registro[nome]) }, t)));
  const formulario = h("form", { class: "filtros", onsubmit: async (evento) => {
    evento.preventDefault();
    const f = evento.currentTarget;
    Object.assign(registro, { unidade: f.unidade.value.trim(), prioridade: f.prioridade.value, desde: f.desde.value, linhas: Number(f.linhas.value) });
    f.querySelector("button").disabled = true;
    c.replaceWith(await cartaoRegistro());
  } },
    h("label", { class: "campo cresce" }, h("span", { class: "rotulo" }, "Unidade"),
      h("input", { name: "unidade", list: "unidades", value: registro.unidade, placeholder: "o sistema todo" })),
    h("datalist", { id: "unidades" }, [...new Set([...UNIDADES_COMUNS, ...(unidadesVistas ?? [])])].sort().map((u) => h("option", { value: u }))),
    campo("Gravidade", opcoes("prioridade", [["", "todas"], ["warning", "avisos e erros"], ["err", "só erros"], ["crit", "só críticos"]])),
    campo("Período", opcoes("desde", [["30min", "30 min"], ["1h", "1 h"], ["6h", "6 h"], ["24h", "24 h"], ["7d", "7 dias"], ["", "tudo"]])),
    campo("Linhas", opcoes("linhas", [[50, "50"], [100, "100"], [200, "200"]])),
    h("button", { type: "submit" }, "Ver"));
  const texto = r.ok === false ? null : r.resultado.trim();
  const log = texto && h("pre", { class: "log" }, texto);
  const c = cartao("Registro do systemd", formulario,
    r.ok === false ? [falha(r), semAcao(r, "servico.journal")]
      : log || h("p", { class: "fraco" }, "Nada no registro com esse filtro."),
    h("p", { class: "fraco" }, "As linhas mais novas ficam embaixo. Segredos saem ocultos."));
  c.classList.add("largo");
  if (log) requestAnimationFrame(() => { log.scrollTop = log.scrollHeight; }); // já na tela: rola até o mais novo
  return c;
}

export async function telaSistema() {
  return Promise.all([cartaoSensores(), cartaoProcessos(), cartaoRede(), cartaoRegistro()]);
}
