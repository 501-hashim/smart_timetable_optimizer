const API_BASE = '/api';

export const api = {
  getClasses: async () => (await fetch(`${API_BASE}/classes`)).json(),
  getSubjects: async () => (await fetch(`${API_BASE}/subjects`)).json(),
  getFaculty: async () => (await fetch(`${API_BASE}/faculty`)).json(),
  getRooms: async () => (await fetch(`${API_BASE}/rooms`)).json(),
  generateTimetable: async (req: any) => {
    const res = await fetch(`${API_BASE}/timetable/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req)
    });
    return res.json();
  },
  getTimetable: async (id: string) => (await fetch(`${API_BASE}/timetable/${id}`)).json(),
  validateTimetable: async (id: string) => {
    const res = await fetch(`${API_BASE}/timetable/validate/${id}`, { method: 'POST' });
    return res.json();
  },
  loadDemo: async () => {
    const res = await fetch(`${API_BASE}/demo/load`, { method: 'POST' });
    return res.json();
  },
  resetDemo: async () => {
    const res = await fetch(`${API_BASE}/demo/reset`, { method: 'POST' });
    return res.json();
  }
};
