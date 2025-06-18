import axios from 'axios';

const API_BASE_URL = 'https://mac.tlampert.net';

export interface Experiment {
  id: string;
  pretty_name: string;
  is_public: boolean;
  created_at: string;
  updated_at: string;
  record_count: number;
}

export interface ExperimentDetails extends Experiment {
  record_counts: {
    typed: number;
    backup: number;
  };
  columns: Array<{
    name: string;
    type: string;
  }>;
}

export interface ExperimentsResponse {
  experiments: Experiment[];
  total_count: number;
}

export interface ExperimentUpdateRequest {
  pretty_name?: string;
  is_public?: boolean;
}

export interface ExperimentData {
  status: string;
  experiment_id: string;
  include_backup: boolean;
  data: Array<Record<string, any>>;
  record_count: number;
  device_ids: string[];
  device_count: number;
  backup_data?: Array<Record<string, any>>;
  backup_record_count?: number;
}

class ExperimentsAPIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ExperimentsAPIError';
  }
}

async function fetchWithAuth(url: string, options: { method?: string; headers?: Record<string, string>; body?: any } = {}) {
  try {
    const response = await axios({
      url,
      method: options.method || 'GET',
      withCredentials: true, // Important for cookies
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      },
      data: options.body
    });

    return response;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      let errorMessage;
      const responseData = error.response?.data;

      if (typeof responseData === 'object') {
        errorMessage = responseData.detail || responseData.message || 'An error occurred';
      } else if (typeof responseData === 'string') {
        errorMessage = responseData;
      } else {
        errorMessage = `HTTP ${error.response?.status || 500}`;
      }

      throw new ExperimentsAPIError(error.response?.status || 500, errorMessage);
    }
    throw error;
  }
}

export const experimentsAPI = {
  /**
   * Get all experiments - no authentication required for public experiments
   */
  async getExperiments(): Promise<ExperimentsResponse> {
    const response = await fetchWithAuth(`${API_BASE_URL}/manage/experiments`);
    return response.data;
  },

  /**
   * Get a specific experiment by ID - no authentication required for public experiments
   */
  async getExperiment(experimentId: string): Promise<ExperimentDetails> {
    const response = await fetchWithAuth(`${API_BASE_URL}/manage/experiments/${experimentId}`);
    return response.data;
  },

  /**
   * Update a specific experiment - requires authentication
   */
  async updateExperiment(experimentId: string, updates: ExperimentUpdateRequest): Promise<Experiment> {
    const response = await fetchWithAuth(`${API_BASE_URL}/manage/experiments/${experimentId}`, {
      method: 'PUT',
      body: updates
    });
    return response.data;
  },

  /**
   * Get all data for all devices in an experiment - uses same auth as other endpoints
   */
  async getExperimentData(experimentId: string, includeBackup: boolean = false): Promise<ExperimentData> {
    const url = `${API_BASE_URL}/query/experiment/${experimentId}/all${includeBackup ? '?backup=true' : ''}`;
    const response = await fetchWithAuth(url);
    return response.data;
  }
};

export { ExperimentsAPIError };