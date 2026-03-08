import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, Shield } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

/**
 * 403 Unauthorized Page
 * Displayed when a user tries to access a resource without proper permissions.
 */
export default function Unauthorized() {
  const navigate = useNavigate();
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          {/* Icon */}
          <div className="mx-auto w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <Shield className="w-8 h-8 text-red-600" />
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Access Denied
          </h1>

          {/* Error Code */}
          <p className="text-sm text-gray-500 font-mono mb-4">HTTP 403 Forbidden</p>

          {/* Description */}
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
              <div className="text-left">
                <p className="text-sm text-gray-700 mb-2">
                  You don't have permission to access this resource.
                </p>
                {user && (
                  <p className="text-xs text-gray-600">
                    Your role: <span className="font-semibold">{user.role}</span>
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Help Text */}
          <p className="text-sm text-gray-600 mb-6">
            If you believe you should have access, please contact your administrator 
            or risk manager.
          </p>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={() => navigate(-1)}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              Go Back
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Go to Dashboard
            </button>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-gray-500 mt-6">
          Need help? Contact <a href="mailto:support@airline.com" className="text-blue-600 hover:underline">support@airline.com</a>
        </p>
      </div>
    </div>
  );
}
