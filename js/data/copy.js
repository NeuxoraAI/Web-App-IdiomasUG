// Rotating multilingual login texts, Bee bot scripted replies, and FAQ list,
// extracted verbatim from the prototype.

export const LANGS = ['es', 'en', 'fr', 'de', 'it', 'pt', 'ja', 'zh', 'ko'];

export const T = {
  tagline: ['El mundo, a tu alcance', 'The world, within your reach', 'Le monde, à ta portée', 'Die Welt in deiner Reichweite', 'Il mondo, a portata di mano', 'O mundo, ao seu alcance', '世界を、あなたの手に', '世界，触手可及', '세계를 당신의 손안에'],
  welcome: ['¡Bienvenida, abeja!', 'Welcome, bee!', 'Bienvenue, abeille !', 'Willkommen, Biene!', 'Benvenuta, ape!', 'Bem-vinda, abelha!', 'ようこそ、ハチさん！', '欢迎，小蜜蜂！', '환영해요, 꿀벌!'],
  title: ['Acceso al examen', 'Exam access', 'Accès à l’examen', 'Zugang zur Prüfung', 'Accesso all’esame', 'Acesso ao exame', '試験へのアクセス', '进入考试', '시험 입장'],
  center: ['Centro de Servicios de Lenguas Extranjeras', 'Foreign Language Services Center', 'Centre de services de langues étrangères', 'Zentrum für Fremdsprachendienste', 'Centro di servizi per le lingue straniere', 'Centro de Serviços de Línguas Estrangeiras', '外国語サービスセンター', '外语服务中心', '외국어 서비스 센터'],
  button: ['Entrar al examen', 'Enter the exam', 'Commencer l’examen', 'Zur Prüfung', 'Inizia l’esame', 'Entrar no exame', '試験を始める', '开始考试', '시험 시작'],
};

// Each entry: array of [text, bold?] segments rendered by the typewriter.
export const TYPED = {
  help: [['Hola, soy '], ['Bee bot', 1], [', powered by Neuxora. Si tienes dudas o preguntas sobre tu acceso o el examen, escríbeme, o contacta directamente a una persona del Centro de Servicios de Lenguas Extranjeras.']],
  faq_code: [['Revisa la carpeta de spam o correo no deseado de tu cuenta institucional. El código se envía desde el Centro hasta 24 horas antes del examen. Si sigue sin llegar, contacta a una persona de servicios al '], ['477 267 49 00 ext. 4751', 1], ['.']],
  faq_invalid: [['Verifica que el formato sea '], ['XXXX-XXXX', 1], [' y que no haya espacios. El código es de '], ['un solo uso', 1], [': si ya se utilizó o el examen se cerró, no volverá a funcionar. En ese caso, comunícate con una persona de servicios.']],
  faq_time: [['El examen dura '], ['35 minutos', 1], [' y tiene 10 preguntas en 3 partes. El cronómetro inicia con la primera pregunta y no se puede pausar; al terminar el tiempo, se envía automáticamente.']],
  faq_human: [['Con gusto. Puedes llamar al '], ['477 267 49 00 ext. 4751', 1], [' de lunes a viernes de 9:00 a 18:00, o acudir a Aquiles Serdán #924, Col. Obregón, León, Gto.']],
  faq_ai: [['IA no disponible en Beta Test. ', 1], ['Por ahora solo puedo responder las preguntas frecuentes. Para cualquier otra duda, contacta directamente a servicios técnicos al '], ['477 267 49 00 ext. 4751', 1], ['.']],
  profile: [['Todo listo, abeja. ', 1], ['Cuando quieras, pulsa '], ['Iniciar examen', 1], ['. El cronómetro de 35 minutos arranca con la primera pregunta y solo tienes un intento.']],
};

export const THINK = ['Pensando…', 'Thinking…', 'Réflexion…', 'Denke nach…', 'Sto pensando…', 'Pensando…', '考え中…', '思考中…', '생각 중…'];

export const FAQS = [
  { key: 'faq_code', q: 'No recibí mi código de acceso' },
  { key: 'faq_invalid', q: 'Mi código no funciona' },
  { key: 'faq_time', q: '¿Cuánto dura el examen?' },
  { key: 'faq_human', q: 'Quiero hablar con una persona de servicios' },
];

// [spanish name, native name, language code]
export const CHIPS = [
  ['Inglés', 'English', 'en'],
  ['Francés', 'Français', 'fr'],
  ['Alemán', 'Deutsch', 'de'],
  ['Italiano', 'Italiano', 'it'],
  ['Portugués', 'Português', 'pt'],
  ['Japonés', '日本語', 'ja'],
  ['Chino', '中文', 'zh'],
  ['Coreano', '한국어', 'ko'],
  ['Español para extranjeros', 'Español', 'es'],
];
