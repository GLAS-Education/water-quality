import axios from 'axios';

const API_BASE_URL = 'https://mac.tlampert.net';

export interface AuthStatus {
  authenticated: boolean;
  user_name?: string;
  team_domain?: string;
}

export interface UserInfo {
  authenticated: boolean;
  user_id: string;
  user_name: string;
  team_domain: string;
  expires_at: number;
}

class AuthAPIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'AuthAPIError';
  }
}

async function fetchWithCredentials(url: string, options: { method?: string; headers?: Record<string, string>; body?: any } = {}) {
  try {
    const response = await axios({
      url,
      method: options.method || 'GET',
      withCredentials: true, // Important for cookies
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {})
      },
      data: options.body // Pass request body if present
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

      throw new AuthAPIError(error.response?.status || 500, errorMessage);
    }
    throw error;
  }
}

export const authAPI = {
  /**
   * Check current authentication status
   */
  async getAuthStatus(): Promise<AuthStatus> {
    const response = await fetchWithCredentials(`${API_BASE_URL}/auth/status`);
    return response.data;
  },

  /**
   * Get current user information (requires authentication)
   */
  async getUserInfo(): Promise<UserInfo> {
    const response = await fetchWithCredentials(`${API_BASE_URL}/auth/me`);
    return response.data;
  },

  /**
   * Initiate login flow (redirects to Slack)
   */
  async login(): Promise<void> {
    // This will redirect to Slack OAuth, so we just navigate
    window.location.href = `${API_BASE_URL}/auth/login`;
  },

  /**
   * Logout current user
   */
  async logout(): Promise<void> {
    await fetchWithCredentials(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
    });
  },
};

export { AuthAPIError }; 