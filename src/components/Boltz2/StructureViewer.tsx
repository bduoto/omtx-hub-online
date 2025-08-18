import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Download, Expand, Minimize, Camera, RotateCcw } from 'lucide-react';
import { ExpandedViewer } from './ExpandedViewer';
import MolstarViewer from './MolstarViewer';

export type ViewerState = 'pre-run' | 'loading' | 'loaded' | 'error' | 'empty';

interface StructureViewerProps {
  cifContent?: string;
  state?: ViewerState;
  title?: string;
  onDownloadCif?: () => void;
  onExpand?: () => void;
  className?: string;
}

export const StructureViewer: React.FC<StructureViewerProps> = ({
  cifContent,
  state = 'pre-run',
  title = 'Structure Viewer',
  onDownloadCif,
  onExpand,
  className = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleExpand = useCallback(() => {
    setIsExpanded(true);
    onExpand?.();
  }, [onExpand]);

  const handleCollapse = useCallback(() => {
    setIsExpanded(false);
  }, []);

  const handleDownloadCif = useCallback(() => {
    if (onDownloadCif) {
      onDownloadCif();
    }
  }, [onDownloadCif]);



  const renderViewerContent = () => {
    switch (state) {
      case 'pre-run':
        return (
          <div className="structure-viewer-placeholder">
            <div className="text-center">
              <div className="text-lg font-medium mb-2 text-white">Interactive 3D Viewer</div>
              <div className="text-sm text-gray-300">
                Run a prediction to view the 3D molecular structure
              </div>
            </div>
          </div>
        );

      case 'loading':
        return (
          <div className="structure-viewer-placeholder structure-viewer-loading">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400 mb-2 mx-auto"></div>
              <div className="text-sm text-white">Loading 3D structure...</div>
              <div className="text-xs text-gray-300 mt-2">
                Initializing NGL viewer and parsing CIF data
              </div>
            </div>
          </div>
        );

      case 'error':
        return (
          <div className="structure-viewer-placeholder structure-viewer-error">
            <div className="text-center">
              <div className="text-lg font-medium mb-2 text-white">❌ Error Loading Structure</div>
              <div className="text-sm text-gray-300 mb-4">
                Unable to load the 3D structure. This may be due to:
              </div>
              <div className="text-xs text-gray-300 mb-4">
                • WebGL not supported by your browser<br/>
                • Large structure file size<br/>
                • Invalid CIF file format
              </div>
              <div className="text-sm text-gray-300">
                Try downloading the CIF file to view in external molecular viewers like ChimeraX or PyMOL.
              </div>
            </div>
          </div>
        );

      case 'empty':
        return (
          <div className="structure-viewer-placeholder">
            <div className="text-center">
              <div className="text-lg font-medium mb-2 text-white">No Structure Available</div>
              <div className="text-sm text-gray-300">
                No structure data found for this prediction
              </div>
            </div>
          </div>
        );

      case 'loaded':
        return (
          <div className="structure-viewer-placeholder">
            <div className="text-center">
              <div className="text-lg font-medium mb-2 text-white">✅ Structure Ready</div>
              <div className="text-sm text-gray-300 mb-4">
                Interactive 3D molecular structure viewer
              </div>
              <div className="text-xs text-gray-300 max-w-md mx-auto">
                Use mouse to rotate, zoom, and explore the molecular structure. 
                Additional controls available in the top-right corner.
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div className="structure-viewer-placeholder">
            <div className="text-center">
              <div className="text-lg font-medium mb-2 text-white">Structure Viewer</div>
              <div className="text-sm text-gray-300">
                Ready to display molecular structures
              </div>
            </div>
          </div>
        );
    }
  };

  const renderControls = () => {
    const hasStructure = state === 'loaded' && cifContent;
    
    return (
      <div className="structure-viewer-controls">
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExpand}
            disabled={!hasStructure}
            className="bg-gray-800 border-gray-600 text-white hover:bg-gray-700"
          >
            <Expand className="w-4 h-4" />
          </Button>
          
          {hasStructure && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDownloadCif}
                disabled={!cifContent}
                className="bg-gray-800 border-gray-600 text-white hover:bg-gray-700"
              >
                <Download className="w-4 h-4" />
              </Button>

            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      <Card className={`${className} bg-gray-900 border-gray-700 min-h-[580px]`}>
        <CardHeader className="pb-3 bg-gray-900 border-b border-gray-700/50 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <CardTitle className="text-xl font-bold bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 bg-clip-text text-transparent tracking-wide drop-shadow-lg filter structure-viewer-title">
              {title}
            </CardTitle>
            <div className="flex items-center gap-2">
              {state === 'loaded' && (
                <Badge variant="secondary" className="text-xs bg-gray-700 text-gray-200">
                  Ready
                </Badge>
              )}
              {state === 'loading' && (
                <Badge variant="secondary" className="text-xs bg-gray-700 text-gray-200">
                  Loading...
                </Badge>
              )}
              {state === 'error' && (
                <Badge variant="destructive" className="text-xs bg-red-800 text-red-200">
                  Error
                </Badge>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="bg-gray-900 pt-6">
          <div className="structure-viewer-container">
            {state === 'loaded' && cifContent ? (
              <MolstarViewer
                cifContent={cifContent}
                state={state}
                onDownloadCif={handleDownloadCif}
                onExpand={handleExpand}
                onScreenshot={(dataUrl) => {
                  // Create a temporary link element to trigger download
                  const link = document.createElement('a');
                  link.href = dataUrl;
                  link.download = `structure_screenshot_${Date.now()}.png`;
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);
                }}
                height={600}
              />
            ) : (
              <>
                {renderViewerContent()}
                {renderControls()}
              </>
            )}
          </div>
          

        </CardContent>
      </Card>

      {isExpanded && (
        <ExpandedViewer
          cifContent={cifContent}
          state={state}
          onClose={handleCollapse}
          onDownloadCif={handleDownloadCif}
        />
      )}
    </>
  );
}; 