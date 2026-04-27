import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 300000, // 5 min — processing can take time
})

export const uploadFiles = async (files) => {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  const { data } = await api.post('/api/jobs', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data // complete JobState
}

export const getDownloadUrl = (jobId, filename) =>
  `${BASE_URL}/api/jobs/${jobId}/download/${filename}`

export const checkHealth = async () => {
  const { data } = await api.get('/api/health')
  return data
}

// Fallback: fetch file content from disk if not embedded in job response
export const getFileContent = async (jobId, filename) => {
  const { data } = await api.get(`/api/jobs/${jobId}/files/${filename}`)
  return data
}
