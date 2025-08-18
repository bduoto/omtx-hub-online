
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { 
  RotateCcw, 
  ZoomIn, 
  ZoomOut, 
  Move3D, 
  Eye, 
  Camera, 
  Settings,
  Maximize,
  Grid3X3,
  Layers,
  Target,
  Compass,
  Sun
} from 'lucide-react';

interface ViewportPanelProps {
  molecule: any;
  viewMode: string;
  onViewModeChange: (mode: string) => void;
}

export const ViewportPanel: React.FC<ViewportPanelProps> = ({
  molecule,
  viewMode,
  onViewModeChange
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showAxes, setShowAxes] = useState(true);
  const [showGrid, setShowGrid] = useState(false);

  const viewModes = [
    { id: 'ball-stick', name: 'Ball & Stick', color: '#E2E756' },
    { id: 'spacefill', name: 'Space Fill', color: '#56E7A4' },
    { id: 'wireframe', name: 'Wireframe', color: '#5B56E7' },
    { id: 'cartoon', name: 'Cartoon', color: '#E7569A' },
    { id: 'surface', name: 'Surface', color: '#56E7A4' },
    { id: 'ribbon', name: 'Ribbon', color: '#E2E756' },
  ];

  return (
    <div className="flex-1 flex flex-col bg-gray-800">
      {/* Enhanced Toolbar */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <h3 className="text-lg font-semibold text-white">
              {molecule ? molecule.name : 'No molecule loaded'}
            </h3>
            {molecule && (
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-400">({molecule.formula})</span>
                <span className="px-2 py-1 text-xs rounded" style={{ backgroundColor: '#5B56E7', color: '#fff' }}>
                  {molecule.type.toUpperCase()}
                </span>
              </div>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-gray-400 hover:text-white"
              onClick={() => setShowGrid(!showGrid)}
            >
              <Grid3X3 className="w-4 h-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-gray-400 hover:text-white"
              onClick={() => setShowAxes(!showAxes)}
            >
              <Compass className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
              <Sun className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
              <Camera className="w-4 h-4" />
            </Button>
            <Button 
              variant="ghost" 
              size="sm" 
              className="text-gray-400 hover:text-white"
              onClick={() => setIsFullscreen(!isFullscreen)}
            >
              <Maximize className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm" className="text-gray-400 hover:text-white">
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Enhanced View Mode Selector */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-400">View:</span>
            <div className="flex space-x-1">
              {viewModes.map((mode) => (
                <Button
                  key={mode.id}
                  size="sm"
                  variant={viewMode === mode.id ? "default" : "ghost"}
                  className={`text-xs ${viewMode === mode.id ? "text-black" : "text-gray-400 hover:text-white"}`}
                  style={viewMode === mode.id ? { backgroundColor: mode.color } : {}}
                  onClick={() => onViewModeChange(mode.id)}
                >
                  {mode.name}
                </Button>
              ))}
            </div>
          </div>
          
          {molecule && (
            <div className="flex items-center space-x-2 text-xs text-gray-400">
              <Target className="w-3 h-3" />
              <span>Center: Origin</span>
            </div>
          )}
        </div>
      </div>

      {/* Enhanced 3D Viewport */}
      <div className="flex-1 relative bg-gray-900">
        {molecule ? (
          <div className="w-full h-full flex items-center justify-center relative">
            {/* Professional placeholder for 3D visualization */}
            <div className="text-center">
              <div 
                className="w-80 h-80 rounded-lg mx-auto mb-4 flex items-center justify-center relative"
                style={{ 
                  background: `radial-gradient(circle at center, ${viewModes.find(m => m.id === viewMode)?.color}15 0%, ${viewModes.find(m => m.id === viewMode)?.color}05 50%, transparent 100%)`,
                  border: `1px solid ${viewModes.find(m => m.id === viewMode)?.color}30`,
                  boxShadow: `inset 0 0 50px ${viewModes.find(m => m.id === viewMode)?.color}10`
                }}
              >
                {/* Coordinate axes */}
                {showAxes && (
                  <div className="absolute top-4 left-4">
                    <div className="flex flex-col space-y-1">
                      <div className="flex items-center text-xs">
                        <div className="w-6 h-0.5 bg-red-500 mr-1"></div>
                        <span className="text-red-400">X</span>
                      </div>
                      <div className="flex items-center text-xs">
                        <div className="w-0.5 h-6 bg-green-500 mr-1"></div>
                        <span className="text-green-400">Y</span>
                      </div>
                      <div className="flex items-center text-xs">
                        <div className="w-1 h-1 bg-blue-500 rounded-full mr-1"></div>
                        <span className="text-blue-400">Z</span>
                      </div>
                    </div>
                  </div>
                )}
                
                {/* Grid overlay */}
                {showGrid && (
                  <div 
                    className="absolute inset-0 opacity-20"
                    style={{
                      backgroundImage: `
                        linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
                      `,
                      backgroundSize: '20px 20px'
                    }}
                  ></div>
                )}
                
                <div className="text-center z-10">
                  <Layers 
                    className="w-20 h-20 mx-auto mb-4" 
                    style={{ color: viewModes.find(m => m.id === viewMode)?.color }} 
                  />
                  <div className="text-white font-medium text-lg">{molecule.name}</div>
                  <div className="text-gray-400 text-sm mb-2">{viewMode.replace('-', ' ')}</div>
                  <div className="text-xs text-gray-500">
                    Professional 3D molecular visualization
                  </div>
                  <div className="text-xs text-gray-600 mt-2">
                    WebGL rendering • Ray tracing ready
                  </div>
                </div>
              </div>
              
              <div className="flex items-center justify-center space-x-4 text-xs text-gray-500">
                <span>Resolution: 1920×1080</span>
                <span>•</span>
                <span>FPS: 60</span>
                <span>•</span>
                <span>Quality: High</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div className="text-center">
              <Grid3X3 className="w-20 h-20 mx-auto mb-4 text-gray-600" />
              <h3 className="text-xl font-medium text-gray-400 mb-2">No Molecule Loaded</h3>
              <p className="text-gray-500 mb-4">
                Select a molecule from the library or upload a structure file
              </p>
              <div className="text-xs text-gray-600">
                Supported: PDB, MOL, MOL2, XYZ, SDF, CIF, GRO, XTC, TRR
              </div>
            </div>
          </div>
        )}

        {/* Enhanced Viewport Controls */}
        <div className="absolute bottom-4 left-4 flex flex-col space-y-2">
          <Button size="sm" variant="secondary" className="w-10 h-10 p-0 bg-gray-700/80 hover:bg-gray-600 backdrop-blur-sm">
            <RotateCcw className="w-4 h-4" />
          </Button>
          <Button size="sm" variant="secondary" className="w-10 h-10 p-0 bg-gray-700/80 hover:bg-gray-600 backdrop-blur-sm">
            <ZoomIn className="w-4 h-4" />
          </Button>
          <Button size="sm" variant="secondary" className="w-10 h-10 p-0 bg-gray-700/80 hover:bg-gray-600 backdrop-blur-sm">
            <ZoomOut className="w-4 h-4" />
          </Button>
          <Button size="sm" variant="secondary" className="w-10 h-10 p-0 bg-gray-700/80 hover:bg-gray-600 backdrop-blur-sm">
            <Move3D className="w-4 h-4" />
          </Button>
          <Button size="sm" variant="secondary" className="w-10 h-10 p-0 bg-gray-700/80 hover:bg-gray-600 backdrop-blur-sm">
            <Target className="w-4 h-4" />
          </Button>
        </div>

        {/* Enhanced Coordinate System */}
        <div className="absolute bottom-4 right-4">
          <div className="bg-gray-800/90 backdrop-blur-sm rounded-lg p-3 text-xs text-gray-400 border border-gray-700">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-gray-500 mb-1">Position</div>
                <div>X: 0.00</div>
                <div>Y: 0.00</div>
                <div>Z: 0.00</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">Rotation</div>
                <div>φ: 0.0°</div>
                <div>θ: 0.0°</div>
                <div>ψ: 0.0°</div>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Indicator */}
        <div className="absolute top-4 right-4">
          <div className="bg-gray-800/80 backdrop-blur-sm rounded px-2 py-1 text-xs text-gray-400 border border-gray-700">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-400 rounded-full"></div>
              <span>WebGL Ready</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
