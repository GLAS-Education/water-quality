import { createRootRoute, Link, Outlet } from '@tanstack/react-router';
import { useAuth } from '../hooks/useAuth';

function AuthSection() {
    const { isAuthenticated, user, login, logout, isLoading, isLoggingIn, isLoggingOut } = useAuth();

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 mr-3">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span className="text-sm">Loading...</span>
            </div>
        );
    }

    if (isAuthenticated && user) {
        return (
            <div className="flex items-center gap-3 mr-3">
                <div className="text-sm">
                    <div className="font-medium">Welcome, {user.user_name}</div>
                    <div className="text-blue-200 text-xs">Org ID: {user.team_domain}</div>
                </div>
                <button
                    onClick={() => logout()}
                    disabled={isLoggingOut}
                    className="cursor-pointer px-3 py-1 text-sm bg-blue-600 hover:bg-blue-500 disabled:bg-blue-400 rounded border border-blue-500 transition-colors"
                >
                    {isLoggingOut ? 'Signing Out...' : 'Sign Out'}
                </button>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2 mr-3">
            <button
                onClick={() => login()}
                disabled={isLoggingIn}
                className="cursor-pointer px-4 py-2 bg-green-600 hover:bg-green-500 disabled:bg-green-400 text-white rounded font-medium transition-colors"
            >
                {isLoggingIn ? 'Signing In...' : 'Sign In with Slack'}
            </button>
        </div>
    );
}

export const Route = createRootRoute({
    component: () => (
        <div className="font-mono h-full">
            <div className="bg-blue-700 text-white flex justify-between border-b-2 border-blue-900">
                <div className="flex items-center gap-2">
                    <img src="/logo.png" alt="GLAS Education Logo" className="w-14 h-14" />
                    <Link to="/" className="p-3 text-xl font-semibold my-auto hover:underline">GLAS-WQ Data</Link>
                </div>
                <div className="flex items-center">
                    <a href="https://glaseducation.org/waterquality" className="p-3 hover:underline my-auto mr-4">About</a>
                    <AuthSection />
                </div>
            </div>
            <Outlet />
            {/* <TanStackRouterDevtools /> */}
        </div>
    )
});