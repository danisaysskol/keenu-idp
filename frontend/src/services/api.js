const BASE_URL = import.meta.env.VITE_API_URL || ''

/**
 * Upload files and stream NDJSON progress updates.
 * onProgress(job) is called after each image is processed.
 * Returns the final complete JobState.
 */
export const uploadFiles = async (files, onProgress) => {
  const form = new FormData()
  for (const file of files) form.append('files', file)

  const response = await fetch(`${BASE_URL}/api/jobs`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    let detail = 'Upload failed'
    try { detail = (await response.json()).detail || detail } catch {}
    throw new Error(detail)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let lastJob = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // keep any incomplete trailing line

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      try {
        const job = JSON.parse(trimmed)
        lastJob = job
        onProgress?.(job)
      } catch {}
    }
  }

  // Handle any remaining buffered content
  if (buffer.trim()) {
    try {
      const job = JSON.parse(buffer.trim())
      lastJob = job
      onProgress?.(job)
    } catch {}
  }

  return lastJob
}

export const getDownloadUrl = (jobId, filename) =>
  `${BASE_URL}/api/jobs/${jobId}/download/${filename}`

export const checkHealth = async () => {
  const res = await fetch(`${BASE_URL}/api/health`)
  return res.json()
}
