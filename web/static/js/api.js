/**
 * API interaction functions for the Medium Scraper application
 */

/**
 * Core API fetch function with loading state management
 * @param {string} endpoint - The API endpoint to call
 * @param {Object} options - Fetch options (method, headers, body, etc.)
 * @returns {Promise} Response data (JSON or blob)
 */
async function apiFetch(endpoint, options = {}) {
  // Set loading state through global reference
  if (window.AppState) {
    window.AppState.isLoading.value = true;
  }
  
  try {
    const res = await fetch(endpoint, options);
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`HTTP ${res.status}: ${errText}`);
    }
    if (options.responseType === 'blob') {
      return await res.blob();
    }
    return await res.json();
  } finally {
    if (window.AppState) {
      window.AppState.isLoading.value = false;
    }
  }
}

/**
 * Builds payload for paginate API requests
 * @param {Object} commonPayload - Common payload settings
 * @param {Object} paginate - Paginate form data
 * @returns {Object} Complete paginate payload
 */
function buildPaginatePayload(commonPayload, paginate) {
  // Validate required fields
  if (!paginate.tag || !paginate.tag.trim()) {
    throw new Error("Tag is required.");
  }
  
  // Validate sender-specific requirements
  if (commonPayload.sender === 'decodo' && (!commonPayload.decodo_api_key || !commonPayload.decodo_api_key.trim())) {
    throw new Error("Decodo API key is required when using Decodo sender.");
  }
  
  const payload = { ...commonPayload, tag: paginate.tag.trim() };
  if (paginate.dateMode === 'ym') {
    if (!paginate.year || !paginate.month) {
      throw new Error("Year and month are required for year/month mode.");
    }
    if (paginate.month < 1 || paginate.month > 12) {
      throw new Error("Month must be between 1 and 12.");
    }
    if (paginate.year < 2000 || paginate.year > 2030) {
      throw new Error("Year must be between 2000 and 2030.");
    }
    payload.year = paginate.year;
    payload.month = paginate.month;
  } else {
    if (!paginate.from_date || !paginate.to_date) {
      throw new Error("From Date and To Date are required for range mode.");
    }
    payload.from_date = paginate.from_date;
    payload.to_date = paginate.to_date;
  }
  return payload;
}

/**
 * Builds payload for scrape API requests
 * @param {Object} commonPayload - Common payload settings
 * @param {Object} scrape - Scrape form data
 * @param {Object} settings - Application settings
 * @returns {Object} Complete scrape payload
 */
function buildScrapePayload(commonPayload, scrape, settings) {
  if (!scrape.urls.trim()) {
    throw new Error("URLs are required.");
  }
  
  // Validate sender-specific requirements
  if (commonPayload.sender === 'decodo' && (!commonPayload.decodo_api_key || !commonPayload.decodo_api_key.trim())) {
    throw new Error("Decodo API key is required when using Decodo sender.");
  }
  
  return {
    ...commonPayload,
    urls: scrape.urls,
    concurrency: settings.concurrency,
  };
}

/**
 * Runs paginate operation (live or job mode)
 * @param {string} mode - 'live' or 'job'
 * @param {Object} commonPayload - Common payload settings
 * @param {Object} paginate - Paginate reactive object
 * @param {Function} setActiveTab - Function to change active tab
 * @param {Function} fetchJobsCallback - Callback to refresh jobs
 */
async function runPaginate(mode, commonPayload, paginate, setActiveTab, fetchJobsCallback) {
  paginate.resultText = 'Paginating...';
  try {
    const payload = buildPaginatePayload(commonPayload, paginate);
    if (mode === 'live') {
      const data = await apiFetch('/api/paginate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      paginate.results = data;
      paginate.resultText = `Found ${data.length} articles.\n\n` + JSON.stringify(data.slice(0, 5), null, 2) + '\n...';
    } else {
      const data = await apiFetch('/api/jobs/paginate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      paginate.resultText = `Started job: ${data.id}. Track its progress in the 'Jobs' tab.`;
      setActiveTab('jobs');
      fetchJobsCallback();
    }
  } catch (e) {
    paginate.resultText = `Error: ${e.message}`;
  }
}

/**
 * Runs scrape operation (live, zip, or job mode)
 * @param {string} mode - 'live', 'zip', or 'job'
 * @param {Object} commonPayload - Common payload settings
 * @param {Object} scrape - Scrape reactive object
 * @param {Object} settings - Application settings
 * @param {Function} setActiveTab - Function to change active tab
 * @param {Function} fetchJobsCallback - Callback to refresh jobs
 */
async function runScrape(mode, commonPayload, scrape, settings, setActiveTab, fetchJobsCallback) {
  scrape.resultText = 'Scraping...';
  try {
    const payload = buildScrapePayload(commonPayload, scrape, settings);
    if (mode === 'live') {
      const data = await apiFetch('/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      scrape.results = data;
      scrape.resultText = `Scraped ${data.length} articles.\n\n` + JSON.stringify(data, null, 2);
    } else if (mode === 'zip') {
      const blob = await apiFetch('/api/scrape-zip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        responseType: 'blob'
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'scrape_results.zip';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      scrape.resultText = 'ZIP download initiated.';
    } else {
      const data = await apiFetch('/api/jobs/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      scrape.resultText = `Started job: ${data.id}. Track its progress in the 'Jobs' tab with real-time updates.`;
      setActiveTab('jobs');
      fetchJobsCallback();
    }
  } catch (e) {
    scrape.resultText = `Error: ${e.message}`;
  }
}

/**
 * Fetches the list of background jobs
 * @param {Object} jobs - Jobs reactive reference
 */
async function fetchJobs(jobs) {
  try {
    const data = await apiFetch('/api/jobs');
    jobs.value = data;
  } catch (e) {
    console.error("Failed to fetch jobs:", e);
  }
}

/**
 * Views details of a specific job and sets up polling for updates
 * @param {string} jobId - The job ID to view
 * @param {Object} selectedJob - Selected job reactive reference
 * @param {Object} isLoadingJobDetail - Loading state reference
 * @param {Object} intervals - Object to store interval references
 */
async function viewJob(jobId, selectedJob, isLoadingJobDetail, intervals) {
  selectedJob.value = { id: jobId };
  isLoadingJobDetail.value = true;
  
  const fetchDetail = async () => {
    try {
      const data = await fetch(`/api/jobs/${jobId}`).then(res => res.json());
      selectedJob.value = data;
      if (data.status === 'done' || data.status === 'error') {
        if (intervals.jobDetailInterval) {
          clearInterval(intervals.jobDetailInterval);
          intervals.jobDetailInterval = null;
        }
      }
    } catch (e) {
      console.error("Failed to fetch job detail:", e);
      if (intervals.jobDetailInterval) {
        clearInterval(intervals.jobDetailInterval);
        intervals.jobDetailInterval = null;
      }
    } finally {
      isLoadingJobDetail.value = false;
    }
  };

  if (intervals.jobDetailInterval) {
    clearInterval(intervals.jobDetailInterval);
  }
  await fetchDetail();
  intervals.jobDetailInterval = setInterval(fetchDetail, 3000);
}

/**
 * Downloads job results as a ZIP file
 * @param {string} jobId - The job ID to download
 * @param {Object} isDownloadingZip - Download state reference
 */
async function downloadJobZip(jobId, isDownloadingZip) {
  isDownloadingZip.value = true;
  try {
    const res = await fetch(`/api/jobs/${jobId}/zip`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${jobId}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e) {
    alert(`Failed to download ZIP: ${e.message}`);
  } finally {
    isDownloadingZip.value = false;
  }
}

/**
 * Uses paginated job output in the scrape form
 * @param {Object} selectedJob - Selected job reactive reference
 * @param {Object} scrape - Scrape reactive object
 * @param {Function} setActiveTab - Function to change active tab
 */
function usePaginatedJobOutput(selectedJob, scrape, setActiveTab) {
  const out = selectedJob.value && selectedJob.value.output;
  let urls = [];
  if (Array.isArray(out)) {
    urls = out.map(item => {
      if (typeof item === 'string') return item;
      if (item && typeof item === 'object' && item.url) return item.url;
      return null;
    }).filter(Boolean);
  }
  if (urls.length) {
    scrape.urls = urls.join('\n');
    setActiveTab('scraper');
  }
}

/**
 * Uses paginated results in the scrape form
 * @param {Object} paginate - Paginate reactive object
 * @param {Object} scrape - Scrape reactive object
 */
function usePaginatedResults(paginate, scrape) {
  if (!paginate.results.length) return;
  const urls = paginate.results.map(r => r.url).filter(Boolean);
  scrape.urls = urls.join('\n');
}

// Export all API functions for use by other modules
window.API = {
  apiFetch,
  buildPaginatePayload,
  buildScrapePayload,
  runPaginate,
  runScrape,
  fetchJobs,
  viewJob,
  downloadJobZip,
  usePaginatedJobOutput,
  usePaginatedResults
};