import React, { useCallback, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Download, X, Camera, RotateCcw } from 'lucide-react';
import MolstarViewer from './MolstarViewer';

export type ViewerState = 'pre-run' | 'loading' | 'loaded' | 'error' | 'empty';

interface ExpandedViewerProps {
  cifContent?: string;
  state?: ViewerState;
  onClose: () => void;
  onDownloadCif?: () => void;
}

export const ExpandedViewer: React.FC<ExpandedViewerProps> = ({
  cifContent,
  state = 'pre-run',
  onClose,
  onDownloadCif
}) => {
  // Handle escape key to close
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const handleDownloadCif = useCallback(() => {
    if (onDownloadCif) {
      onDownloadCif();
    }
  }, [onDownloadCif]);



  const renderContent = () => {
    switch (state) {
      case 'pre-run':
        return (
          <div className="text-center">
                          <div className="text-2xl font-medium mb-4 text-white">Interactive 3D Viewer</div>
            <div className="text-lg text-gray-300">
              Run a prediction to view the 3D molecular structure
            </div>
          </div>
        );

      case 'loading':
        return (
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-400 mb-4 mx-auto"></div>
            <div className="text-lg text-white">Loading 3D structure...</div>
            <div className="text-sm text-gray-300 mt-2">
              Initializing NGL viewer and parsing molecular data
            </div>
          </div>
        );

      case 'error':
        return (
          <div className="text-center">
            <div className="text-2xl font-medium mb-4 text-white">❌ Error Loading Structure</div>
            <div className="text-lg text-gray-300 mb-4">
              Unable to load the 3D structure in full screen mode.
            </div>
            <div className="text-sm text-gray-300 mb-6">
              This may be due to WebGL limitations, large file size, or invalid CIF format.
            </div>
            <div className="text-base text-gray-300">
              Try downloading the CIF file to view in external molecular viewers like ChimeraX or PyMOL.
            </div>
          </div>
        );

      case 'empty':
        return (
          <div className="text-center">
            <div className="text-2xl font-medium mb-4 text-white">No Structure Available</div>
            <div className="text-lg text-gray-300">
              No structure data found for this prediction
            </div>
          </div>
        );

      case 'loaded':
        return (
          <div className="text-center">
            <div className="text-3xl font-medium mb-4 text-white">✅ Interactive 3D Structure</div>
            <div className="text-xl text-gray-300 mb-6">
              Full-screen molecular visualization
            </div>
            <div className="text-base text-gray-300 max-w-2xl mx-auto">
              Use mouse to rotate, zoom, and explore the molecular structure. 
              Controls in the top-right corner provide additional visualization options.
            </div>
          </div>
        );

      default:
        return (
          <div className="text-center">
                          <div className="text-2xl font-medium mb-4 text-white">Structure Viewer</div>
            <div className="text-lg text-gray-300">
              Ready to display molecular structures
            </div>
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="w-full h-full max-w-screen-2xl max-h-screen bg-gray-900 border border-gray-700 rounded-lg shadow-xl overflow-hidden relative">
        {/* Header with controls */}
        <div className="absolute top-0 left-0 right-0 h-16 bg-gray-900 border-b border-gray-700 flex items-center justify-between px-6 z-20">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-bold bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent tracking-wide structure-viewer-title">
            Structure Viewer
          </h2>
          {state === 'loaded' && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">•</span>
              <span className="text-sm text-gray-400">Structure loaded</span>
            </div>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {state === 'loaded' && cifContent && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadCif}
                disabled={!cifContent}
                className="bg-gray-800 border-gray-600 text-white hover:bg-gray-700"
              >
                <Download className="w-4 h-4 mr-2" />
                Download CIF
              </Button>

            </>
          )}
          
          <Button
            variant="outline"
            size="sm"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onClose();
            }}
            className="bg-gray-800 border-gray-600 text-white hover:bg-gray-700"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Main content area */}
      <div className="absolute top-16 left-0 right-0 bottom-0 overflow-auto">
        <div className="p-8 min-h-full">
          <div className="max-w-6xl mx-auto">
            {state === 'loaded' && cifContent ? (
              <div className="mb-12">
                <MolstarViewer
                  cifContent={cifContent}
                  state={state}
                  onDownloadCif={handleDownloadCif}
                  onScreenshot={(dataUrl) => {
                    // Create a temporary link element to trigger download
                    const link = document.createElement('a');
                    link.href = dataUrl;
                    link.download = `structure_screenshot_${Date.now()}.png`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  }}
                  height={700}
                  className="w-full"
                />
                <div className="mt-8 text-center">
                  <p className="text-gray-400 text-sm">
                    Use mouse to rotate, zoom, and explore the molecular structure. Use the control buttons to adjust the view and download options.
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center min-h-[700px]">
                {renderContent()}
              </div>
            )}
          </div>
        </div>
      </div>


      </div>
    </div>
  );
}; 