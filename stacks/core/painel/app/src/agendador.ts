// Agendador do painel: roda ações do executor na hora marcada ("ligar o PC às 19h nos dias úteis").
// Fica no painel, e não em timers do systemd, porque criar timers exige root. Com o painel fora do ar
// na hora, ao voltar ele roda o que atrasou até a tolerância (15 min por padrão); passou disso, a
// execução vira "perdida" e o celular fica sabendo. Assim um "ligar o PC às 19h" não roda às 3h.
// As horas são as do fuso do container (TZ do compose).
import type { Banco, LinhaAgendamento } from "./banco.ts";
import type { RespostaExecutor } from "./executor.ts";

export type Quando =
  | { tipo: "uma_vez"; em: number } // instante, em ms
  | { tipo: "semana"; dias: number[]; hora: string } // 0 = domingo; "HH:MM"
  | { tipo: "mes"; dia: number; hora: string }; // dia 1-31 (mês mais curto: o último dia)

// o que dá para agendar, e o parâmetro que cada uma pede
export const AGENDAVEIS: Record<string, string | null> = {
  "pc.ligar": null,
  "pc.desligar": null,
  "pc.reiniciar": null,
  "servico.reiniciar": "stack",
  "app.reiniciar": "projeto",
  "app.parar": "projeto",
  "app.publicar": "projeto",
};
export const AVISOS = ["falha", "sempre", "nunca"];
const NOMES: Record<string, string> = {
  "pc.ligar": "Ligar o PC", "pc.desligar": "Desligar o PC", "pc.reiniciar": "Reiniciar o PC",
  "servico.reiniciar": "Reiniciar", "app.reiniciar": "Reiniciar o app", "app.parar": "Parar o app",
  "app.publicar": "Publicar o app",
};
const TERMINADOS = new Set(["concluido", "falhou", "recusado", "expirado", "cancelado"]);
const NOME_ALVO = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const HORA = /^([01]\d|2[0-3]):[0-5]\d$/;

export class EntradaInvalida extends Error {}

function noHorario(base: Date, hora: string): Date {
  const [h, m] = hora.split(":").map(Number);
  const d = new Date(base);
  d.setHours(h, m, 0, 0);
  return d;
}

// a próxima vez depois de "depois" (ms), ou null se não há mais
export function proxima(q: Quando, depois: number): number | null {
  if (q.tipo === "uma_vez") return q.em > depois ? q.em : null;
  const inicio = new Date(depois);
  if (q.tipo === "semana") {
    for (let i = 0; i <= 7; i++) {
      const dia = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + i);
      const vez = noHorario(dia, q.hora);
      if (q.dias.includes(vez.getDay()) && vez.getTime() > depois) return vez.getTime();
    }
    return null;
  }
  for (let i = 0; i <= 12; i++) {
    const ultimo = new Date(inicio.getFullYear(), inicio.getMonth() + i + 1, 0).getDate();
    const vez = noHorario(new Date(inicio.getFullYear(), inicio.getMonth() + i, Math.min(q.dia, ultimo)), q.hora);
    if (vez.getTime() > depois) return vez.getTime();
  }
  return null;
}

export type Entrada = {
  id?: number;
  nome: string;
  acao: string;
  params: Record<string, string>;
  quando: Quando;
  aviso: string;
  tolerancia: number;
};

// confere o que veio da tela; erros em português, para mostrar como estão
export function validar(e: Record<string, unknown>): Entrada {
  const acao = String(e.acao ?? "");
  if (!(acao in AGENDAVEIS)) throw new EntradaInvalida(`não dá para agendar ${acao || "essa ação"}`);
  const alvo = AGENDAVEIS[acao];
  const p = (e.params ?? {}) as Record<string, unknown>;
  if (typeof p !== "object" || Array.isArray(p)) throw new EntradaInvalida("params deve ser um objeto");
  const params: Record<string, string> = {};
  if (alvo) {
    if (typeof p[alvo] !== "string" || !NOME_ALVO.test(p[alvo] as string)) throw new EntradaInvalida(`escolha o ${alvo}`);
    params[alvo] = p[alvo] as string;
  }
  const q = (e.quando ?? {}) as Record<string, unknown>;
  let quando: Quando;
  if (q.tipo === "uma_vez") {
    if (typeof q.em !== "number" || !Number.isFinite(q.em)) throw new EntradaInvalida("escolha a data e a hora");
    quando = { tipo: "uma_vez", em: q.em };
  } else if (q.tipo === "semana") {
    const dias = Array.isArray(q.dias) ? [...new Set(q.dias)] : [];
    if (!dias.length || !dias.every((d) => Number.isInteger(d) && (d as number) >= 0 && (d as number) <= 6))
      throw new EntradaInvalida("escolha pelo menos um dia da semana");
    if (typeof q.hora !== "string" || !HORA.test(q.hora)) throw new EntradaInvalida("hora deve ser como 19:00");
    quando = { tipo: "semana", dias: (dias as number[]).sort(), hora: q.hora };
  } else if (q.tipo === "mes") {
    if (!Number.isInteger(q.dia) || (q.dia as number) < 1 || (q.dia as number) > 31) throw new EntradaInvalida("dia do mês deve ser de 1 a 31");
    if (typeof q.hora !== "string" || !HORA.test(q.hora)) throw new EntradaInvalida("hora deve ser como 19:00");
    quando = { tipo: "mes", dia: q.dia as number, hora: q.hora };
  } else throw new EntradaInvalida("quando deve ser uma vez, toda semana ou todo mês");
  const aviso = String(e.aviso ?? "falha");
  if (!AVISOS.includes(aviso)) throw new EntradaInvalida("aviso deve ser falha, sempre ou nunca");
  const tolerancia = Number(e.tolerancia ?? 15);
  if (!Number.isInteger(tolerancia) || tolerancia < 1 || tolerancia > 24 * 60) throw new EntradaInvalida("tolerância deve ser de 1 a 1440 min");
  const nome = String(e.nome ?? "").trim().slice(0, 80) || `${NOMES[acao]}${alvo ? ` ${params[alvo]}` : ""}`;
  const id = e.id === undefined || e.id === null ? undefined : Number(e.id);
  if (id !== undefined && !Number.isInteger(id)) throw new EntradaInvalida("id inválido");
  return { id, nome, acao, params, quando, aviso, tolerancia };
}

export type Agendamento = Omit<LinhaAgendamento, "params" | "quando" | "ativo"> & {
  params: Record<string, string>;
  quando: Quando;
  ativo: boolean;
};

export function ler(linha: LinhaAgendamento): Agendamento {
  return { ...linha, params: JSON.parse(linha.params), quando: JSON.parse(linha.quando), ativo: linha.ativo === 1 };
}

type Executar = (metodo: "GET" | "POST", caminho: string, corpo?: unknown) => Promise<RespostaExecutor>;

const resumir = (corpo: Record<string, unknown>) => {
  const texto = JSON.stringify(corpo.resultado ?? corpo.resumo ?? "");
  return texto.length > 300 ? texto.slice(0, 300) + "…" : texto;
};

export class Agendador {
  rodando = new Set<number>();
  relogio: ReturnType<typeof setInterval> | null = null;
  banco: Banco;
  executar: Executar;
  agora: () => number;
  esperaPedido: number;

  // esperaPedido: segundos por consulta ao pedido (o executor segura até a resposta)
  constructor(banco: Banco, executar: Executar, agora: () => number = Date.now, esperaPedido = 60) {
    this.banco = banco;
    this.executar = executar;
    this.agora = agora;
    this.esperaPedido = esperaPedido;
  }

  iniciar(intervalo = 20_000) {
    this.tique().catch((e) => console.error("agendador:", e));
    this.relogio = setInterval(() => this.tique().catch((e) => console.error("agendador:", e)), intervalo);
    this.relogio.unref();
  }

  parar() {
    if (this.relogio) clearInterval(this.relogio);
  }

  // roda o que venceu; devolve as execuções começadas (os testes esperam por elas)
  async tique(): Promise<Promise<string>[]> {
    const agora = this.agora();
    const comecadas: Promise<string>[] = [];
    for (const linha of this.banco.agendamentos()) {
      const a = ler(linha);
      if (!a.ativo || a.proxima === null || a.proxima > agora) continue;
      const seguinte = proxima(a.quando, agora);
      this.banco.marcarAgendamento(a.id, { proxima: seguinte, ativo: seguinte !== null });
      if (agora - a.proxima <= a.tolerancia * 60_000) comecadas.push(this.rodar(a));
      else comecadas.push(this.perder(a));
    }
    return comecadas;
  }

  async perder(a: Agendamento): Promise<string> {
    const era = new Date(a.proxima!).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
    const motivo = `era para ${era}; o painel estava fora do ar e passou da tolerância de ${a.tolerancia} min`;
    this.banco.registrar(a.acao, a.params, "perdida", motivo, null, a.id);
    this.banco.marcarAgendamento(a.id, { ultima: this.agora(), ultimo_estado: "perdida" });
    if (a.aviso !== "nunca") await this.avisar(`Agendamento perdido: ${a.nome}`, motivo);
    return "perdida";
  }

  async rodar(a: Agendamento): Promise<string> {
    if (this.rodando.has(a.id)) return "já rodando"; // nunca duas execuções do mesmo ao mesmo tempo
    this.rodando.add(a.id);
    const registro = this.banco.registrar(a.acao, a.params, "executando", "", null, a.id);
    let estado = "falhou";
    let resumo = "";
    try {
      let r = await this.executar("POST", `/acao/${a.acao}`, { params: a.params, origem: "agendamento" });
      if (r.status === 202 && r.corpo.pedido) {
        const pedido = String(r.corpo.pedido);
        this.banco.atualizarRegistro(registro, { pedido });
        // uma publicação pode levar até 15 min; depois de 30 consultas, desiste de esperar
        for (let i = 0; i < 30; i++) {
          r = await this.executar("GET", `/pedido/${pedido}?esperar=${this.esperaPedido}`);
          const p = r.corpo.pedido as Record<string, unknown> | undefined;
          if (!p) break;
          if (TERMINADOS.has(String(p.estado))) {
            estado = String(p.estado);
            resumo = estado === "concluido" ? resumir(p) : String(p.erro ?? p.resumo ?? estado);
            break;
          }
          estado = "executando";
          resumo = "o painel parou de esperar; confira no executor";
        }
        if (!r.corpo.pedido && r.corpo.ok === false) resumo = String(r.corpo.erro ?? "erro");
      } else if (r.corpo.ok === false) resumo = String(r.corpo.erro ?? "erro");
      else {
        estado = "concluido";
        resumo = resumir(r.corpo);
      }
    } catch (e) {
      resumo = `o executor não respondeu: ${(e as Error).message}`;
    } finally {
      this.rodando.delete(a.id);
    }
    this.banco.atualizarRegistro(registro, { estado, resumo });
    this.banco.marcarAgendamento(a.id, { ultima: this.agora(), ultimo_estado: estado });
    if (a.aviso === "sempre" || (a.aviso === "falha" && estado !== "concluido"))
      await this.avisar(estado === "concluido" ? `Feito: ${a.nome}` : `Agendamento falhou: ${a.nome}`, resumo);
    return estado;
  }

  async avisar(titulo: string, texto: string) {
    try {
      const r = await this.executar("POST", "/acao/aviso.celular", { params: { titulo: titulo.slice(0, 120), texto }, origem: "agendamento" });
      if (r.corpo.ok === false) console.error("agendador: aviso não saiu:", r.corpo.erro);
    } catch (e) {
      console.error("agendador: aviso não saiu:", (e as Error).message);
    }
  }
}
