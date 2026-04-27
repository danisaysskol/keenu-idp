// Static manifest of bundled sample images (served from /public/samples/).
// Each entry: { url: string, filename: string }

const s = (category, filename) => ({
  url: `/samples/${category}/${filename}`,
  filename,
  category,
})

export const SAMPLE_CATEGORIES = [
  {
    id: 'cnic',
    label: 'CNIC',
    emoji: '🪪',
    images: [
      s('cnic', '-522-_jpg.rf.502f61c1e26a3b0de24f94621e909670.jpg'),
      s('cnic', '-735-_jpg.rf.b46e540a3c3ce1993c2848f9ccbca36d.jpg'),
      s('cnic', '-640-_jpg.rf.aaf993501ab0b7fe2c98c4b33584d0ad.jpg'),
      s('cnic', '-818-_jpg.rf.f777a3ce906f2c7c611dcb87f5dd3f22.jpg'),
      s('cnic', '-624-_jpg.rf.1b7c626964fdee8d952a7e2ebbc0822c.jpg'),
    ],
  },
  {
    id: 'driving_licence',
    label: 'Driving Licence',
    emoji: '🚗',
    images: [
      s('driving_licence', 'dl128_jpg.rf.ba121726311d39d74e87cf4c273e7aef.jpg'),
      s('driving_licence', 'dl113_jpg.rf.b60a197dce64fc0da32b012ddfce8ee2.jpg'),
      s('driving_licence', 'dl61_jpg.rf.9b2f65e9aeb55a44beaf30556dbc6344.jpg'),
      s('driving_licence', 'dl101_jpg.rf.0faca65b470d8ddeadfb6ab9b2c40120.jpg'),
      s('driving_licence', 'dl131_jpg.rf.07d0d841c7a9e8ab5317fc55e3b7aa72.jpg'),
    ],
  },
  {
    id: 'forms',
    label: 'Forms',
    emoji: '📋',
    images: [
      s('forms', '0060308251.png'),
      s('forms', '0013255595.png'),
      s('forms', '0060025670.png'),
      s('forms', '0030041455.png'),
      s('forms', '80718412_8413.png'),
    ],
  },
  {
    id: 'invoices',
    label: 'Invoices',
    emoji: '🧾',
    images: [
      s('invoices', 'batch1-0044.jpg'),
      s('invoices', 'batch1-0033.jpg'),
      s('invoices', 'batch1-0014.jpg'),
      s('invoices', 'batch1-0025.jpg'),
      s('invoices', 'batch1-0024.jpg'),
    ],
  },
  {
    id: 'receipt',
    label: 'Receipt',
    emoji: '🛒',
    images: [
      s('receipt', 'receipt_00406.png'),
      s('receipt', 'receipt_00569.png'),
      s('receipt', 'receipt_00402.png'),
      s('receipt', 'receipt_00519.png'),
      s('receipt', 'receipt_00747.png'),
    ],
  },
  {
    id: 'resumes',
    label: 'Resume / CV',
    emoji: '📄',
    images: [
      s('resumes', '4.png'),
      s('resumes', '45.png'),
      s('resumes', '193.png'),
      s('resumes', '86.png'),
      s('resumes', '42.png'),
    ],
  },
]
