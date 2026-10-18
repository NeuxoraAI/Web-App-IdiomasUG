// Central mutable app state. Screens read and write it directly and
// call their own render functions after mutating (no reactive runtime).

export const state = {
  screen: 'login',
  curp: '',
  code: '',
  perfil: null,       // GET /api/perfil
  resultado: null,    // POST /api/intento/finalizar

  // Exam
  q: 0,               // current question index
  answers: {},        // question index -> answer (index, string, or array)
  secondsLeft: 0,
  totalSeconds: 0,
  checked: false,     // instant-feedback: current answer has been checked
  pick: null,         // drag/order: currently picked word-bank index
  pickL: null,        // match: currently selected left tile index
  playing: false,     // listening question: audio animation active

  // Results
  closeIn: 20,        // auto-logout countdown on the results screen
};

export function resetExam() {
  state.q = 0;
  state.answers = {};
  state.checked = false;
  state.pick = null;
  state.pickL = null;
  state.playing = false;
}

export const folio = () => state.perfil?.folio || '';
