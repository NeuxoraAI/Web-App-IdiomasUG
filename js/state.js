// Central mutable app state. Screens read and write it directly and
// call their own render functions after mutating (no reactive runtime).

export const state = {
  screen: 'login',
  email: '',
  curp: '',

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
  certOpen: false,
};

export function resetExam() {
  state.q = 0;
  state.answers = {};
  state.checked = false;
  state.pick = null;
  state.pickL = null;
  state.playing = false;
}

// Demo folio derived from the access code typed at login
export function folio() {
  const clean = (state.email || '').replace(/[^A-Za-z0-9]/g, '').toUpperCase();
  return 'EXAUBI-2026B-' + (clean || 'A7K2Q9');
}
