import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState, useMemo } from 'react';
import { useExperiments } from '../hooks/useExperiments';
import { useAuth } from '../hooks/useAuth';
import type { Experiment } from '../api/experiments';

export const Route = createFileRoute('/')({
    component: Index,
});

function Index() {
    const [search, setSearch] = useState('');
    const { data: experimentsData, isLoading, error, isError } = useExperiments();
    const { user, isAuthenticated, authStatus } = useAuth();
    const navigate = useNavigate();

    // Filter experiments based on search
    const filteredExperiments = useMemo(() => {
        if (!experimentsData?.experiments) return [];
        
        if (!search.trim()) return experimentsData.experiments;
        
        const searchLower = search.toLowerCase();
        return experimentsData.experiments.filter(experiment => 
            experiment.id.toLowerCase().includes(searchLower) ||
            experiment.pretty_name.toLowerCase().includes(searchLower)
        );
    }, [experimentsData?.experiments, search]);

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
        });
    };

    const formatDateTime = (dateString: string) => {
        return new Date(dateString).toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        });
    };

    return (
        <>
            <div className="bg-blue-400 h-[25vh] flex items-center justify-center border-b-2 border-blue-900">
                <div className="w-[60%] text-center space-y-4">
                    <h1 className="text-4xl font-bold text-white">Water Quality Project</h1>
                    <p className="text-gray-100">The water quality project is a device comprised of several sensors designed to help us better understand Geneva Lake through data. You can browse the data we've collected below.</p>
                </div>
            </div>

            <div className="p-8 max-w-7xl mx-auto">
                <div className="flex flex-col gap-4">
                    <div>
                        <div className="flex justify-between items-center">
                            <h2 className="text-2xl font-bold">Browse Experiments</h2>
                            <div className="flex gap-4 items-center w-[35%]">
                                <input
                                    type="text"
                                    value={search}
                                    onChange={(e) => setSearch(e.target.value)}
                                    placeholder="Filter by name or ID..."
                                    className="w-full px-4 py-2 border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Authentication Notice */}
                    {/* {!user && (
                        <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                            <div className="flex justify-between items-center">
                                <div className="flex">
                                    <div className="ml-3">
                                        <h3 className="text-sm font-medium text-blue-800">
                                            Sign in to View Experiments
                                        </h3>
                                        <div className="mt-2 text-sm text-blue-700">
                                            <p>Authentication is required to view water quality experiment data.</p>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex-shrink-0">
                                    <button
                                        onClick={() => window.location.href = 'https://mac.tlampert.net/auth/login'}
                                        className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                                    >
                                        Sign In
                                    </button>
                                </div>
                            </div>
                        </div>
                    )} */}

                    <div className="overflow-x-auto">
                        <table className="min-w-full border border-gray-200">
                            <thead>
                                <tr className="bg-gray-50">
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Start Date</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Updated</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Records</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {!user && (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                                            <div className="flex flex-col items-center space-y-2">
                                                <span className="text-lg">🔒</span>
                                                <span>Sign in to view private experiments</span>
                                            </div>
                                        </td>
                                    </tr>
                                )}

                                {user && isLoading && (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                                            <div className="flex items-center justify-center">
                                                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                                                <span className="ml-2">Loading experiments...</span>
                                            </div>
                                        </td>
                                    </tr>
                                )}
                                
                                {user && isError && (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-4 text-center text-red-500">
                                            <div className="flex flex-col items-center">
                                                <span className="font-medium">Error loading experiments</span>
                                                <span className="text-sm text-gray-500 mt-1">
                                                    {error?.message || 'Please try again later.'}
                                                </span>
                                            </div>
                                        </td>
                                    </tr>
                                )}

                                {user && !isLoading && !isError && filteredExperiments.length === 0 && (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                                            {search.trim() ? 'No experiments match your search.' : 'No experiments found.'}
                                        </td>
                                    </tr>
                                )}

                                {!isLoading && !isError && filteredExperiments.map((experiment: Experiment) => (
                                    <tr 
                                        key={experiment.id} 
                                        className="hover:bg-gray-50 cursor-pointer transition-colors"
                                        onClick={() => navigate({ to: '/$id', params: { id: experiment.id } })}
                                    >
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="text-blue-600 font-medium">
                                                {experiment.id}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-gray-900">
                                                {experiment.pretty_name}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {formatDate(experiment.created_at)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {formatDateTime(experiment.updated_at)}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {experiment.record_count.toLocaleString()}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                                                experiment.is_public 
                                                    ? 'bg-green-100 text-green-800' 
                                                    : 'bg-yellow-100 text-yellow-800'
                                            }`}>
                                                {experiment.is_public ? 'Public' : 'Private'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Results summary */}
                    {user && !isLoading && !isError && experimentsData && (
                        <div className="text-sm text-gray-600 mt-4">
                            Showing {filteredExperiments.length} of {experimentsData.total_count} experiments
                            {search.trim() && ` matching "${search}"`}
                        </div>
                    )}
                </div>
            </div>
        </>
    )
}