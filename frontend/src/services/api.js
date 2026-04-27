import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

export const uploadFiles = async (files) => {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  const { data } = await api.post('/api/jobs', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export const getJobStatus = async (jobId) => {
  const { data } = await api.get(`/api/jobs/${jobId}`)
  return data
}

export const listJobFiles = async (jobId) => {
  const { data } = await api.get(`/api/jobs/${jobId}/files`)
  return data
}

export const getFileContent = async (jobId, filename) => {
  const { data } = await api.get(`/api/jobs/${jobId}/files/${filename}`)
  return data
}

export const getDownloadUrl = (jobId, filename) =>
  `${BASE_URL}/api/jobs/${jobId}/download/${filename}`

export const checkHealth = async () => {
  const { data } = await api.get('/api/health')
  return data
}
