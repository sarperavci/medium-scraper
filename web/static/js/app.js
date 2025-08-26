const { createApp, ref, reactive, onMounted, onUnmounted, watch, computed } = Vue;

createApp({
  setup() {
    const activeTab = ref('scraper');
    const isLoading = ref(false);
    const jobs = ref([]);
    const selectedJob = ref(null);
    const isLoadingJobDetail = ref(false);
    const isDownloadingZip = ref(false);
    const jobProgress = ref({});
    const activeWebSockets = ref({});
    let jobsInterval = null;
    let jobDetailInterval = null;

    // Set up global state reference for API module
    window.AppState = {
      isLoading
    };

    // Create intervals object for API module
    const intervals = {
      jobDetailInterval: null
    };

    const settings = reactive({
      expanded: true,
      sender: 'decodo',
      decodo_api_key: '',
      advanced: false,
      timeout: 30,
      proxies: '',
      concurrency: 10,
      disable_cache: false,
    });

    const paginate = reactive({
      tag: 'tryhackme',
      dateMode: 'ym',
      year: window.Utils.getCurrentYear(),
      month: window.Utils.getCurrentMonth(),
      from_date: '',
      to_date: '',
      results: [],
      resultText: 'Paginate results will appear here.',
    });

    const scrape = reactive({
      urls: '',
      results: [],
      resultText: 'Scrape results will appear here.',
    });

    // Use truncate function from Utils module
    const truncate = window.Utils.truncate;
    
    // WebSocket management for progress tracking
    const connectToJob = (jobId) => {
      if (activeWebSockets.value[jobId]) {
        return; // Already connected
      }
      
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/progress/${jobId}`;
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        activeWebSockets.value[jobId] = ws;
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'progress') {
          jobProgress.value[jobId] = data;
          
          // If job is completed (100%), close the WebSocket after a delay
          if (data.percentage >= 100) {
            setTimeout(() => {
              disconnectFromJob(jobId);
            }, 2000); // Keep progress visible for 2 seconds after completion
          }
        }
      };
      
      ws.onclose = () => {
        delete activeWebSockets.value[jobId];
        // Don't delete progress data immediately - let it persist for completed jobs
        // delete jobProgress.value[jobId];
      };
      
      ws.onerror = () => {
        delete activeWebSockets.value[jobId];
      };
    };
    
    const disconnectFromJob = (jobId) => {
      if (activeWebSockets.value[jobId]) {
        activeWebSockets.value[jobId].close();
        delete activeWebSockets.value[jobId];
      }
    };
    
    const truncateUrl = (url, maxLength = 50) => {
      if (!url) return '';
      return url.length > maxLength ? url.substring(0, maxLength) + '...' : url;
    };
    
    const cleanupOldProgress = () => {
      const currentJobIds = new Set(jobs.value.map(job => job.id));
      Object.keys(jobProgress.value).forEach(jobId => {
        if (!currentJobIds.has(jobId)) {
          delete jobProgress.value[jobId];
        }
      });
    };

    const commonPayload = computed(() => {
      const payload = {
        sender: settings.sender,
        advanced: settings.advanced,
        timeout: settings.timeout,
        disable_cache: settings.disable_cache,
      };
      if (settings.decodo_api_key) payload.decodo_api_key = settings.decodo_api_key;
      if (settings.proxies) payload.proxies = settings.proxies;
      return payload;
    });

    // API function wrappers that use the external API module
    const runPaginate = (mode) => {
      window.API.runPaginate(mode, commonPayload.value, paginate, (tab) => activeTab.value = tab, fetchJobs);
    };

    const usePaginatedResults = () => {
      window.API.usePaginatedResults(paginate, scrape);
    };

    const runScrape = (mode) => {
      window.API.runScrape(mode, commonPayload.value, scrape, settings, (tab) => activeTab.value = tab, fetchJobs);
    };

    const fetchJobs = () => {
      window.API.fetchJobs(jobs);
      
      // Clean up old progress data
      cleanupOldProgress();
      
      // Connect to WebSocket for any running jobs, but only if not already connected
      jobs.value.forEach(job => {
        if (job.status === 'running' && !activeWebSockets.value[job.id]) {
          connectToJob(job.id);
        } else if (job.status !== 'running' && activeWebSockets.value[job.id]) {
          // Disconnect from completed jobs
          disconnectFromJob(job.id);
        }
      });
    };
    
    const viewJob = (jobId) => {
      intervals.jobDetailInterval = jobDetailInterval;
      window.API.viewJob(jobId, selectedJob, isLoadingJobDetail, intervals);
      jobDetailInterval = intervals.jobDetailInterval;
      
      // Connect to WebSocket for progress updates only if it's a running job and not already connected
      const job = jobs.value.find(j => j.id === jobId);
      if (job && job.status === 'running' && !activeWebSockets.value[jobId]) {
        connectToJob(jobId);
      }
    };

    const downloadJobZip = (jobId) => {
      window.API.downloadJobZip(jobId, isDownloadingZip);
    };

    const usePaginatedJobOutput = () => {
      window.API.usePaginatedJobOutput(selectedJob, scrape, (tab) => activeTab.value = tab);
    };

    watch(activeTab, (newTab) => {
      if (newTab === 'jobs') {
        fetchJobs();
        if (jobsInterval) clearInterval(jobsInterval);
        jobsInterval = setInterval(fetchJobs, 5000);
      } else {
        if (jobsInterval) clearInterval(jobsInterval);
      }
    });
    
    watch(selectedJob, (newJob, oldJob) => {
      if (!newJob && jobDetailInterval) {
          clearInterval(jobDetailInterval);
          jobDetailInterval = null;
      }
      
      // Disconnect from old job WebSocket
      if (oldJob && oldJob.id) {
        disconnectFromJob(oldJob.id);
      }
      
      // Connect to new job WebSocket if it's running
      if (newJob && newJob.id && newJob.status === 'running') {
        connectToJob(newJob.id);
      }
    });
    
    onMounted(() => {
      paginate.to_date = window.Utils.getCurrentDateISO();
      paginate.from_date = window.Utils.getFirstDayOfMonthISO();
    });

    onUnmounted(() => {
      if (jobsInterval) clearInterval(jobsInterval);
      if (jobDetailInterval) clearInterval(jobDetailInterval);
      
      // Close all WebSocket connections
      Object.keys(activeWebSockets.value).forEach(jobId => {
        disconnectFromJob(jobId);
      });
    });

    return {
      activeTab,
      isLoading,
      settings,
      paginate,
      scrape,
      jobs,
      selectedJob,
      isLoadingJobDetail,
      isDownloadingZip,
      runPaginate,
      usePaginatedResults,
      runScrape,
      fetchJobs,
      viewJob,
      downloadJobZip,
      truncate,
      truncateUrl,
      usePaginatedJobOutput,
      jobProgress,
    };
  }
}).mount('#app');