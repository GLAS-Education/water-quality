import { createFileRoute } from '@tanstack/react-router';
import { useEffect, useState } from 'react';
import { useExperiment, useUpdateExperiment, useExperimentData } from '../hooks/useExperiments';
import { useAuth } from '../hooks/useAuth';
import DataAnalysis from '../components/DataAnalysis';

export const Route = createFileRoute('/$id')({
    component: Experiment
});

function Experiment() {
    const { id } = Route.useParams();
    const { data: experiment, isLoading, error, refetch } = useExperiment(id);
    const { data: experimentData } = useExperimentData(id);
    const { isAuthenticated } = useAuth();
    const updateMutation = useUpdateExperiment();

    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editForm, setEditForm] = useState({
        pretty_name: '',
        is_public: false
    });
    const [selectedDeviceId, setSelectedDeviceId] = useState<string | 'all'>('all');

    useEffect(() => {
        // Initialize form when experiment data loads
        if (experiment && editForm.pretty_name === '') {
            setEditForm({
                pretty_name: experiment.pretty_name,
                is_public: experiment.is_public
            });
        }
    }, []);

    // Reset selected device when experiment data changes
    useEffect(() => {
        if (experimentData?.device_ids?.length) {
            setSelectedDeviceId('all');
        }
    }, [experimentData?.device_ids]);

    const handleEditClick = () => {
        if (experiment) {
            setEditForm({
                pretty_name: experiment.pretty_name,
                is_public: experiment.is_public
            });
            setIsEditModalOpen(true);
        }
    };

    const handleSave = async () => {
        if (!experiment) return;

        try {
            await updateMutation.mutateAsync({
                experimentId: experiment.id,
                updates: editForm
            });
            setIsEditModalOpen(false);
            refetch(); // Refresh the data
        } catch (error) {
            console.error('Failed to update experiment:', error);
            // TODO: Show error toast
        }
    };

    const handleCancel = () => {
        setIsEditModalOpen(false);
        if (experiment) {
            setEditForm({
                pretty_name: experiment.pretty_name,
                is_public: experiment.is_public
            });
        }
    };

    if (isLoading) {
        return (
            <div className="p-6">
                <div className="animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
                    <div className="h-4 bg-gray-200 rounded w-1/6 mb-2"></div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6">
                <div className="text-red-600 bg-red-50 p-4 rounded-lg">
                    <h2 className="font-semibold mb-2">Error loading experiment</h2>
                    <p>{error.message}</p>
                </div>
            </div>
        );
    }

    if (!experiment) {
        return (
            <div className="p-6">
                <div className="text-gray-600">
                    <h2 className="text-xl font-semibold mb-2">Experiment not found</h2>
                    <p>The experiment "{id}" could not be found or you don't have permission to view it.</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8">
            {/* Header with experiment name and edit button */}
            <div className="flex items-start justify-between mb-6">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 mb-2">
                        {experiment.pretty_name}
                    </h1>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                        <span className="flex items-center">
                            <span className={`inline-block w-2 h-2 rounded-full mr-2 ${experiment.is_public ? 'bg-green-500' : 'bg-gray-400'
                                }`}></span>
                            {experiment.is_public ? 'Public' : 'Private'}
                        </span>
                        <span>ID: {experiment.id}</span>
                        <span>{experiment.record_counts.typed} records</span>
                    </div>
                </div>

                {isAuthenticated && (
                    <button
                        onClick={handleEditClick}
                        className="cursor-pointer px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        Edit
                    </button>
                )}
            </div>

            {/* Edit Modal */}
            {isEditModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-md">
                        <h2 className="text-xl font-semibold mb-4">Edit Experiment</h2>

                        <div className="space-y-4">
                            <div>
                                <label htmlFor="pretty_name" className="block text-sm font-medium text-gray-700 mb-1">
                                    Name
                                </label>
                                <input
                                    type="text"
                                    id="pretty_name"
                                    value={editForm.pretty_name}
                                    onChange={(e) => setEditForm(prev => ({
                                        ...prev,
                                        pretty_name: e.target.value
                                    }))}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>

                            <div>
                                <label className="flex items-center">
                                    <input
                                        type="checkbox"
                                        checked={editForm.is_public}
                                        onChange={(e) => setEditForm(prev => ({
                                            ...prev,
                                            is_public: e.target.checked
                                        }))}
                                        className="mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                    />
                                    <span className="text-sm font-medium text-gray-700">
                                        Make this experiment public
                                    </span>
                                </label>
                                <p className="text-xs text-gray-500 mt-1">
                                    Public experiments can be viewed by anyone without authentication
                                </p>
                            </div>
                        </div>

                        <div className="flex justify-end space-x-3 mt-6">
                            <button
                                onClick={handleCancel}
                                disabled={updateMutation.isPending}
                                className="cursor-pointer px-4 py-2 text-gray-700 bg-gray-200 rounded-lg hover:bg-gray-300 transition-colors disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={updateMutation.isPending}
                                className="cursor-pointer px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                            >
                                {updateMutation.isPending ? 'Saving...' : 'Save'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Device Tab Selector */}
            {experimentData?.device_ids && experimentData.device_ids.length > 1 && (
                <div className="mb-6">
                    <h3 className="text-lg font-medium text-gray-900 mb-3">Device Data</h3>
                    <div className="border-b border-gray-200">
                        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
                            <button
                                onClick={() => setSelectedDeviceId('all')}
                                className={`cursor-pointer whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                                    selectedDeviceId === 'all'
                                        ? 'border-blue-500 text-blue-600'
                                        : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                }`}
                            >
                                All Devices ({experimentData.device_count})
                            </button>
                            {experimentData.device_ids.map(deviceId => (
                                <button
                                    key={deviceId}
                                    onClick={() => setSelectedDeviceId(deviceId)}
                                    className={`cursor-pointer whitespace-nowrap py-2 px-1 border-b-2 font-medium text-sm ${
                                        selectedDeviceId === deviceId
                                            ? 'border-blue-500 text-blue-600'
                                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                                    }`}
                                >
                                    {deviceId}
                                </button>
                            ))}
                        </nav>
                    </div>
                </div>
            )}

            <div className="mt-8">
                <DataAnalysis experimentId={experiment.id} selectedDeviceId={selectedDeviceId} />
            </div>
        </div>
    );
}