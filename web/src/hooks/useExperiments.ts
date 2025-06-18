import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { experimentsAPI, type ExperimentsResponse, type ExperimentDetails, type ExperimentUpdateRequest, type Experiment, type ExperimentData } from '../api/experiments';
import { useAuthStatus } from './useAuth';

export const useExperiments = () => {
  const { data: authData } = useAuthStatus();
  
  return useQuery<ExperimentsResponse>({
    queryKey: ['experiments', authData?.authenticated],
    queryFn: () => experimentsAPI.getExperiments(),
    enabled: true,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 30 * 1000,
    retry: (failureCount, error: any) => {
      // Don't retry on authentication errors
      if (error?.status === 401 || error?.status === 403) {
        return false;
      }
      return failureCount < 3;
    },
  });
};

export const useExperiment = (experimentId: string) => {
  return useQuery<ExperimentDetails>({
    queryKey: ['experiment', experimentId],
    queryFn: () => experimentsAPI.getExperiment(experimentId),
    enabled: !!experimentId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, error: any) => {
      // Don't retry on not found or forbidden errors
      if (error?.status === 404 || error?.status === 403) {
        return false;
      }
      return failureCount < 3;
    },
  });
};

export const useUpdateExperiment = () => {
  const queryClient = useQueryClient();

  return useMutation<Experiment, Error, { experimentId: string; updates: ExperimentUpdateRequest }>({
    mutationFn: ({ experimentId, updates }) => experimentsAPI.updateExperiment(experimentId, updates),
    onSuccess: (updatedExperiment, { experimentId }) => {
      // Update the single experiment query cache
      queryClient.setQueryData(['experiment', experimentId], (oldData: ExperimentDetails | undefined) => {
        if (oldData) {
          return {
            ...oldData,
            ...updatedExperiment,
          };
        }
        return oldData;
      });

      // Update the experiments list cache
      queryClient.setQueryData(['experiments'], (oldData: ExperimentsResponse | undefined) => {
        if (oldData) {
          return {
            ...oldData,
            experiments: oldData.experiments.map(exp => 
              exp.id === experimentId ? { ...exp, ...updatedExperiment } : exp
            ),
          };
        }
        return oldData;
      });
    },
  });
};

export const useExperimentData = (experimentId: string, includeBackup: boolean = false) => {
  return useQuery<ExperimentData>({
    queryKey: ['experimentData', experimentId, includeBackup],
    queryFn: () => experimentsAPI.getExperimentData(experimentId, includeBackup),
    enabled: !!experimentId,
    staleTime: 2 * 60 * 1000, // 2 minutes (shorter than experiment metadata since data changes more frequently)
    retry: (failureCount, error: any) => {
      // Don't retry on not found, forbidden, or auth errors
      if (error?.status === 404 || error?.status === 403 || error?.status === 401) {
        return false;
      }
      return failureCount < 3;
    },
  });
}; 