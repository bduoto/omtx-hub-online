
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { 
  Layers, 
  Eye, 
  EyeOff, 
  Grid3X3, 
  Zap,
  Atom,
  Waves
} from 'lucide-react';

interface AdvancedViewportProps {
  molecule: any;
  viewMode: string;
  onViewModeChange: (mode: string) => void;
}

export const AdvancedViewport: React.FC<AdvancedViewportProps> = ({
  molecule,
  viewMode,
  onViewModeChange
}) => {
  const [showSurface, setShowSurface] = useState(false);
  const [showElectronDensity, setShowElectronDensity] = useState(false);
  const [surfaceOpacity, setSurfaceOpacity] = useState([70]);
  const [densityContour, setDensityContour] = useState([50]);

  const advancedModes = [
    { id: 'surface', name: 'Surface', color: '#56E7A4', icon: Layers },
    { id: 'electron-density', name: 'Electron Density', color: '#5B56E7', icon: Zap },
    { id: 'electrostatic', name: 'Electrostatic', color: '#E7569A', icon: Atom },
    { id: 'cavity', name: 'Cavities', color: '#E2E756', icon: Waves },
  ];

  return (
    <div className="absolute top-16 right-4 w-64 bg-gray-800/95 backdrop-blur-sm border border-gray-700 rounded-lg p-4 space-y-4">
      <h4 className="text-sm font-semibold text-white">Advanced Visualization</h4>
      
      {/* Surface Controls */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-300">Molecular Surface</span>
          <Button
            size="sm"
            variant="ghost"
            className="w-8 h-8 p-0"
            onClick={() => setShowSurface(!showSurface)}
          >
            {showSurface ? 
              <Eye className="w-4 h-4 text-green-400" /> : 
              <EyeOff className="w-4 h-4 text-gray-500" />
            }
          </Button>
        </div>
        
        {showSurface && (
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs text-gray-400">Opacity</label>
              <span className="text-xs text-white">{surfaceOpacity[0]}%</span>
            </div>
            <Slider
              value={surfaceOpacity}
              onValueChange={setSurfaceOpacity}
              max={100}
              step={1}
              className="w-full"
            />
          </div>
        )}
      </div>

      {/* Electron Density Controls */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-300">Electron Density</span>
          <Button
            size="sm"
            variant="ghost"
            className="w-8 h-8 p-0"
            onClick={() => setShowElectronDensity(!showElectronDensity)}
          >
            {showElectronDensity ? 
              <Eye className="w-4 h-4 text-blue-400" /> : 
              <EyeOff className="w-4 h-4 text-gray-500" />
            }
          </Button>
        </div>
        
        {showElectronDensity && (
          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs text-gray-400">Contour Level</label>
              <span className="text-xs text-white">{densityContour[0]}%</span>
            </div>
            <Slider
              value={densityContour}
              onValueChange={setDensityContour}
              max={100}
              step={1}
              className="w-full"
            />
          </div>
        )}
      </div>

      {/* Advanced Mode Buttons */}
      <div className="space-y-1">
        <label className="text-xs text-gray-400">Visualization Modes</label>
        {advancedModes.map((mode) => (
          <Button
            key={mode.id}
            size="sm"
            variant="ghost"
            className="w-full justify-start text-gray-300 hover:text-white"
            style={{ color: mode.color }}
            onClick={() => onViewModeChange(mode.id)}
          >
            <mode.icon className="w-4 h-4 mr-2" />
            {mode.name}
          </Button>
        ))}
      </div>

      {/* Visualization Info */}
      {molecule && (
        <div className="pt-2 border-t border-gray-700">
          <div className="text-xs text-gray-400 space-y-1">
            <div>Current: {viewMode.replace('-', ' ')}</div>
            <div className="flex items-center">
              <Grid3X3 className="w-3 h-3 mr-1" />
              Ready for rendering
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
