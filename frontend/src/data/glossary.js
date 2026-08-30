export const GLOSSARY_ENTRIES = [
  {
    id: "beat",
    term: "Beat",
    fullName: "Señal de salud",
    definition:
      "Un Beat es un evento o señal de salud autenticada: un mensaje que emite un System, firmado con JWT y clasificado por un tipo de Beat. El Operator lo ve en su panel y, cuando aplica, es el origen de una notificación en Monitor.",
  },
  {
    id: "beatlab",
    term: "BeatLab",
    fullName: "El SaaS",
    definition:
      "BeatLab es el producto: un SaaS para controlar la salud de los Systems de una empresa. El dominio gira en torno a quién compra (la empresa), quién observa (el Operator), quién emite (el System), cómo se clasifica el mensaje (tipo de Beat) y el mensaje en sí (el Beat).",
  },
  {
    id: "demo",
    term: "Demo",
    fullName: "Prueba del Hub",
    definition:
      "La demo es el periodo de prueba del Hub de una empresa: 15 días con 10.000 Beats. En ese tiempo se pueden dar de alta Operators, Systems y tipos de Beat y ver el flujo real. No es un producto aparte: es el mismo Hub, con un cupo temporal.",
  },
  {
    id: "empresa",
    term: "Empresa",
    fullName: "La cliente",
    definition:
      "La empresa es la cliente de BeatLab. Se le vende un Hub: su centro para controlar la salud de sus Systems. No hay un nombre oficial extra para la empresa ni para quien administra el Hub; Operator es quien usa Monitor.",
  },
  {
    id: "hub",
    term: "Hub",
    fullName: "Centro de la empresa",
    definition:
      "El Hub es el centro que se vende a cada empresa para controlar la salud de sus Systems. Desde ahí se dan de alta Operators, Systems (con JWT) y tipos de Beat; también se validan, persisten y enrutan los Beats de esa empresa.",
  },
  {
    id: "monitor",
    term: "Monitor",
    fullName: "App del Operator",
    definition:
      "Monitor es la app nativa en React Native. Es la superficie del Operator: su panel personal de Beats y notificaciones, siempre acotado a su empresa. No es el Hub; el alta de Operators se hace desde el Hub, no desde Monitor.",
  },
  {
    id: "operator",
    term: "Operator",
    fullName: "Persona que observa",
    definition:
      "Un Operator es una persona de una empresa con acceso a Monitor y a su panel: ve los Beats que le corresponden (de los Systems de su empresa) y recibe notificaciones. Se da de alta desde el Hub de su empresa, no desde Monitor. Un Operator no es un System.",
  },
  {
    id: "system",
    term: "System",
    fullName: "Aplicación que emite Beats",
    definition:
      "Un System es una aplicación o proceso que envía automáticamente señales de vida (Beats) al Hub para indicar que está funcionando y reportar su estado.",
    examplesLabel: "Ejemplos de System:",
    examples: [
      "Una aplicación web.",
      "Una aplicación móvil.",
      "Una API.",
      "Un servicio en segundo plano.",
      "Un proceso programado (job).",
    ],
  },
  {
    id: "tipo-de-beat",
    term: "Tipo de Beat",
    fullName: "Clasificación del mensaje",
    definition:
      "Etiqueta con la que se clasifica un Beat. El Hub de la empresa define los tipos disponibles. Un Beat siempre pertenece a un tipo; no hay mensajes sin categoría. Ejemplos ilustrativos, no cerrados: alerta, aviso, confirmación, error, estado.",
  },
];

export function getGlossaryEntry(id) {
  return GLOSSARY_ENTRIES.find((entry) => entry.id === id);
}
