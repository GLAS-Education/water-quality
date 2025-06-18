import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { authAPI, AuthStatus, UserInfo, AuthAPIError } from '../api/auth';

// Query keys for consistent caching
export const authKeys = {
  status: ['auth', 'status'] as const,
  user: ['auth', 'user'] as const,
};

/**
 * Hook to check authentication status
 * This is lightweight and checked frequently
 */
export function useAuthStatus() {
  return useQuery({
    queryKey: authKeys.status,
    queryFn: authAPI.getAuthStatus,
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: (failureCount, error) => {
      // Don't retry on client errors
      if (error instanceof AuthAPIError && error.status >= 400 && error.status < 500) {
        return false;
      }
      return failureCount < 2;
    },
  });
}

/**
 * Hook to get detailed user information (only when authenticated)
 */
export function useUserInfo(enabled = true) {
  return useQuery({
    queryKey: authKeys.user,
    queryFn: authAPI.getUserInfo,
    enabled,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, error) => {
      // Don't retry on authentication errors
      if (error instanceof AuthAPIError && (error.status === 401 || error.status === 403)) {
        return false;
      }
      return failureCount < 2;
    },
  });
}

/**
 * Hook for login functionality
 */
export function useLogin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authAPI.login,
    onSuccess: () => {
      // Invalidate auth queries after successful login
      queryClient.invalidateQueries({ queryKey: authKeys.status });
      queryClient.invalidateQueries({ queryKey: authKeys.user });
    },
  });
}

/**
 * Hook for logout functionality
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authAPI.logout,
    onSuccess: () => {
      // Clear all auth-related data after logout
      queryClient.setQueryData(authKeys.status, { authenticated: false });
      queryClient.removeQueries({ queryKey: authKeys.user });
      
      // Optionally clear all queries if user data might be sensitive
      // queryClient.clear();
    },
    onError: (error) => {
      console.error('Logout failed:', error);
      // Even if logout fails on server, clear local auth state
      queryClient.setQueryData(authKeys.status, { authenticated: false });
      queryClient.removeQueries({ queryKey: authKeys.user });
    },
  });
}

/**
 * Combined hook that provides all auth functionality
 */
export function useAuth() {
  const authStatusQuery = useAuthStatus();
  const userInfoQuery = useUserInfo(authStatusQuery.data?.authenticated);
  const loginMutation = useLogin();
  const logoutMutation = useLogout();

  const isAuthenticated = authStatusQuery.data?.authenticated ?? false;
  const isLoading = authStatusQuery.isLoading || (isAuthenticated && userInfoQuery.isLoading);
  const error = authStatusQuery.error || userInfoQuery.error;

  return {
    // Status
    isAuthenticated,
    isLoading,
    error,
    
    // Data
    authStatus: authStatusQuery.data,
    user: userInfoQuery.data,
    
    // Actions
    login: loginMutation.mutate,
    logout: logoutMutation.mutate,
    
    // Mutation states
    isLoggingIn: loginMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
    
    // Refetch functions
    refetchAuthStatus: authStatusQuery.refetch,
    refetchUser: userInfoQuery.refetch,
  };
} 