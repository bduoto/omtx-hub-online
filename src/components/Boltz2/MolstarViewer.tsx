import React, { useState, useCallback, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  Download, 
  Expand, 
  Camera, 
  RotateCcw, 
  Loader2, 
  AlertCircle, 
  FileText, 
  Settings, 
  ChevronDown,
  ChevronUp,
  Ruler,
  Target,
  Mouse,
  Info,
  Palette,
  RotateCw
} from 'lucide-react';

export type ViewerState = 'loading' | 'loaded' | 'error' | 'empty';

interface MolstarViewerProps {
  cifContent?: string;
  state?: ViewerState;
  onDownloadCif?: () => void;
  onExpand?: () => void;
  onScreenshot?: (dataUrl: string) => void;
  className?: string;
  height?: number;
}

// Color schemes for molecular visualization
const COLOR_SCHEMES = [
  { value: 'element', label: 'Element' },
  { value: 'chainid', label: 'Chain ID' },
  { value: 'bfactor', label: 'B-factor' },
  { value: 'hydrophobicity', label: 'Hydrophobicity' },
  { value: 'sstruc', label: 'Secondary Structure' },
  { value: 'residueindex', label: 'Residue Index' },
  { value: 'resname', label: 'Residue Name' },
  { value: 'atomindex', label: 'Atom Index' },
  { value: 'modelindex', label: 'Model Index' },
  { value: 'partialcharge', label: 'Partial Charge' },
  { value: 'electrostatic', label: 'Electrostatic' },
  { value: 'uniform', label: 'Uniform' }
];

// Define which color schemes override manual colors based on Mol* hierarchy
const COLOR_SCHEME_OVERRIDES = {
  // Residue Properties - these override manual colors completely
  'hydrophobicity': true,
  'sstruc': true, // Secondary Structure
  'bfactor': true,
  'residueindex': true,
  'resname': true,
  'partialcharge': true,
  'electrostatic': true,
  
  // Chain/Structural Properties - these can coexist with manual colors
  'chainid': false,
  'element': false,
  'atomindex': false,
  'modelindex': false,
  
  // Manual coloring - fully uses manual colors
  'uniform': false
};

// Selection presets for different molecular components
const SELECTION_PRESETS = [
  { value: 'protein', label: 'Protein', selection: 'protein' },
  { value: 'ligand', label: 'Ligand', selection: 'hetero and not water' },
  { value: 'water', label: 'Water', selection: 'water' },
  { value: 'ions', label: 'Ions', selection: 'ion' },
  { value: 'backbone', label: 'Backbone', selection: 'backbone' },
  { value: 'sidechains', label: 'Sidechains', selection: 'sidechain' },
  { value: 'aromatic', label: 'Aromatic', selection: 'aromatic' },
  { value: 'charged', label: 'Charged', selection: 'charged' },
  { value: 'hydrophobic', label: 'Hydrophobic', selection: 'hydrophobic' }
];

// Disabled color picker component that shows override indicator
const DisabledColorPicker: React.FC<{
  title?: string;
}> = ({ title = "Overridden by color scheme" }) => {
  return (
    <div className="relative">
      <Button
        variant="outline"
        size="sm"
        className="w-6 h-6 p-0 border-gray-600 cursor-not-allowed opacity-75"
        disabled
      >
        <div className="w-4 h-4 rounded-sm border border-gray-400 bg-white relative">
          {/* Red diagonal line */}
          <div 
            className="absolute inset-0 bg-red-500 transform rotate-45 origin-center"
            style={{ 
              width: '1px', 
              height: 'calc(100% * 1.414)', 
              left: '50%',
              top: '50%',
              transformOrigin: 'center',
              transform: 'translate(-50%, -50%) rotate(45deg)'
            }}
          />
        </div>
      </Button>
      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-800 text-white text-xs rounded whitespace-nowrap opacity-0 hover:opacity-100 transition-opacity pointer-events-none z-50">
        {title}
      </div>
    </div>
  );
};

// Color picker component
const ColorPicker: React.FC<{
  color: string;
  onChange: (color: string) => void;
  disabled?: boolean;
  overridden?: boolean;
}> = ({ color, onChange, disabled = false, overridden = false }) => {
  const [localColor, setLocalColor] = useState(color);
  const [isOpen, setIsOpen] = useState(false);

  const handleColorChange = (newColor: string) => {
    setLocalColor(newColor);
    onChange(newColor);
  };

  const handleHexChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value.startsWith('#') && value.length <= 7) {
      setLocalColor(value);
      if (value.length === 7) {
        onChange(value);
      }
    }
  };

  // Show disabled picker when overridden by color scheme
  if (overridden) {
    return <DisabledColorPicker title="Overridden by color scheme" />;
  }

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="w-6 h-6 p-0 border-gray-600 hover:border-gray-500"
          disabled={disabled}
        >
          <div 
            className="w-4 h-4 rounded-sm border border-gray-400"
            style={{ backgroundColor: color }}
          />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 bg-gray-800 border-gray-600 text-white">
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="hex-input" className="text-xs text-gray-400">
              Hex Color
            </Label>
            <Input
              id="hex-input"
              type="text"
              value={localColor}
              onChange={handleHexChange}
              className="bg-gray-700 border-gray-600 text-white"
              placeholder="#000000"
            />
          </div>
          
          <div className="space-y-2">
            <Label className="text-xs text-gray-400">Color Picker</Label>
            <input
              type="color"
              value={color}
              onChange={(e) => handleColorChange(e.target.value)}
              className="w-full h-10 bg-gray-700 border border-gray-600 rounded cursor-pointer"
            />
          </div>
          
          <div className="space-y-2">
            <Label className="text-xs text-gray-400">Quick Colors</Label>
            <div className="grid grid-cols-8 gap-1">
              {[
                '#4A90E2', '#7ED321', '#F5A623', '#D0021B', 
                '#BD10E0', '#50E3C2', '#B8E986', '#9013FE',
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
                '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
              ].map((presetColor) => (
                <button
                  key={presetColor}
                  onClick={() => handleColorChange(presetColor)}
                  className="w-6 h-6 rounded border border-gray-600 hover:border-gray-400 cursor-pointer"
                  style={{ backgroundColor: presetColor }}
                />
              ))}
            </div>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
};

// Simple fallback viewer for when no CIF content is available
const EmptyViewer: React.FC<{
  height: number;
  className: string;
  state: ViewerState;
}> = ({ height, className, state }) => {
  const renderContent = () => {
    switch (state) {
      case 'loading':
        return (
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-blue-400" />
            <div className="text-sm text-gray-300">Loading structure...</div>
          </div>
        );
      case 'error':
        return (
          <div className="text-center">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 text-red-400" />
            <div className="text-sm font-medium mb-2 text-white">Error Loading Structure</div>
            <div className="text-xs text-gray-300">Please try again or check the file format</div>
          </div>
        );
      case 'empty':
      default:
        return (
          <div className="text-center">
            <FileText className="h-8 w-8 mx-auto mb-2 text-gray-400" />
            <div className="text-sm font-medium mb-2 text-white">No Structure Available</div>
            <div className="text-xs text-gray-300">
              Complete a prediction to view 3D structure
            </div>
          </div>
        );
    }
  };

  return (
    <div className={`relative bg-gray-900 border border-gray-700 rounded-lg overflow-hidden ${className}`} style={{ height }}>
      <div className="absolute inset-0 flex items-center justify-center p-4">
        {renderContent()}
      </div>
    </div>
  );
};

const MolstarViewer: React.FC<MolstarViewerProps> = ({
  cifContent,
  state = 'empty',
  onDownloadCif,
  onExpand,
  onScreenshot,
  className = '',
  height = 400
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<any>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [structureLoaded, setStructureLoaded] = useState(false);
  
  // Advanced controls state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [colorScheme, setColorScheme] = useState('element');
  const [selectedPreset, setSelectedPreset] = useState('protein');
  const [measurementMode, setMeasurementMode] = useState(false);
  const [showBindingSites, setShowBindingSites] = useState(false);
  const [showMouseControls, setShowMouseControls] = useState(false);
  
  // Representation visibility state
  const [representationVisibility, setRepresentationVisibility] = useState({
    cartoon: true,
    'ball+stick': true,
    surface: false // Surface off by default
  });

  // Color state for representations
  const [cartoonColor, setCartoonColor] = useState('#4A90E2'); // Default cartoon color
  const [ballStickColor, setBallStickColor] = useState('#7ED321'); // Default ball+stick color
  const [surfaceColor, setSurfaceColor] = useState('#F5A623'); // Default surface color

  // Initialize NGL Viewer
  const initializeNGL = useCallback(async () => {
    // Skip if no container OR if already initialized AND stage exists
    if (!containerRef.current || (isInitialized && stageRef.current)) {
      return;
    }

    // If we have isInitialized=true but no stage, we need to re-initialize
    if (isInitialized && !stageRef.current) {
      setIsInitialized(false);
    }

    try {
      setIsLoading(true);
      setError(null);

      // Dynamic import of NGL to avoid build-time issues
      const NGL = await import('ngl');

      // Create NGL stage
      const stage = new NGL.Stage(containerRef.current, {
        backgroundColor: '#0f0f0f', // Dark theme background
        quality: 'high',
        sampleLevel: 2,
        cameraType: 'perspective',
        clipNear: 0.1,
        clipFar: 1000,
        fogNear: 50,
        fogFar: 100,
        impostor: true,
        workerDefault: true,
        rotateSpeed: 2.0,
        zoomSpeed: 1.2,
        panSpeed: 1.0,
        mousePreset: 'default'
      });

      // Handle window resize
      const handleResize = () => {
        if (stage) {
          stage.handleResize();
          // Force re-render after resize
          setTimeout(() => {
            if (stage) {
              stage.viewer.render();
            }
          }, 100);
        }
      };

      window.addEventListener('resize', handleResize);

      stageRef.current = stage;
      setIsInitialized(true);
      setIsLoading(false);
    } catch (err) {
      console.error('Failed to initialize NGL:', err);
      setError('Failed to initialize 3D viewer. Please refresh the page.');
      setIsLoading(false);
    }
  }, []);

  // Load CIF content into NGL
  const loadCifContent = useCallback(async (content: string) => {
    if (!stageRef.current || !content) {
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      setStructureLoaded(false);

      // Clear previous structures
      stageRef.current.removeAllComponents();

      // Create a blob from the CIF content
      const blob = new Blob([content], { type: 'chemical/x-cif' });
      const file = new File([blob], 'structure.cif', { type: 'chemical/x-cif' });

      // Load structure from CIF data
      const component = await stageRef.current.loadFile(file, {
        ext: 'cif',
        format: 'cif'
      });

      // Determine if we should use color scheme or manual colors based on hierarchy
      const colorSchemeOverrides = COLOR_SCHEME_OVERRIDES[colorScheme] || false;
      const isUniform = colorScheme === 'uniform';
      
      // For uniform: use manual colors completely
      // For non-overriding schemes (chainid, element): use color scheme as base, allow manual override
      // For overriding schemes (hydrophobicity, sstruc): use color scheme completely
      const effectiveCartoonColor = isUniform ? cartoonColor : 
                                   colorSchemeOverrides ? colorScheme : 
                                   cartoonColor; // Allow manual override for non-overriding schemes
      const effectiveBallStickColor = isUniform ? ballStickColor : 
                                     colorSchemeOverrides ? colorScheme : 
                                     ballStickColor; // Allow manual override for non-overriding schemes
      const effectiveSurfaceColor = isUniform ? surfaceColor : 
                                   colorSchemeOverrides ? colorScheme : 
                                   surfaceColor; // Allow manual override for non-overriding schemes

      // Add cartoon representation for proteins
      if (representationVisibility.cartoon) {
        component.addRepresentation('cartoon', {
          color: effectiveCartoonColor,
          opacity: 0.9,
          smoothSheet: true,
          aspectRatio: 5.0,
          radialSegments: 16,
          capped: true
        });
      }

      // Add ball-and-stick representation for ligands and small molecules
      // Always use element coloring for natural atomic colors
      if (representationVisibility['ball+stick']) {
        component.addRepresentation('ball+stick', {
          color: 'element',
          opacity: 1.0,
          radiusScale: 0.3,
          aspectRatio: 1.5,
          radiusSegments: 12,
          sphereDetail: 2,
          radialSegments: 8,
          openEnded: false,
          disableImpostor: false,
          sele: 'not protein and not nucleic'
        });
      }

      // Add surface representation for better visualization
      if (representationVisibility.surface) {
        component.addRepresentation('surface', {
          color: effectiveSurfaceColor,
          opacity: 0.15,
          surfaceType: 'ms',
          probeRadius: 1.4,
          scaleFactor: 2.0,
          cutoff: 0.0,
          contour: true,
          sele: 'protein'
        });
      }

      // Auto-center and zoom to fit with better positioning (zoomed out for better view)
      stageRef.current.autoView(1000, true);
      
      setStructureLoaded(true);
      setIsLoading(false);
    } catch (err) {
      console.error('Failed to load CIF content:', err);
      setError('Failed to load structure. Please check the CIF file format.');
      setIsLoading(false);
    }
  }, [representationVisibility, cartoonColor, ballStickColor, surfaceColor, colorScheme]);

  // Handle screenshot
  const handleScreenshot = useCallback(() => {
    if (stageRef.current && onScreenshot) {
      stageRef.current.makeImage({
        factor: 2,
        antialias: true,
        trim: true,
        transparent: false
      }).then((blob: Blob) => {
        const url = URL.createObjectURL(blob);
        onScreenshot(url);
      });
    }
  }, [onScreenshot]);

  // Handle reset view
  const handleResetView = useCallback(() => {
    if (stageRef.current) {
      // Reset camera controls to default state
      const viewer = stageRef.current.viewer;
      if (viewer && viewer.controls) {
        // Reset rotation and position
        viewer.controls.reset();
      }
      
      // Center and fit the structure
      stageRef.current.autoView(1000, true);
    }
  }, []);

  // Toggle representation visibility
  const toggleRepresentation = useCallback((type: keyof typeof representationVisibility) => {
    setRepresentationVisibility(prev => ({
      ...prev,
      [type]: !prev[type]
    }));
  }, []);

  // Handle color changes for representations
  const handleCartoonColorChange = useCallback((color: string) => {
    setCartoonColor(color);
    // Reload content to apply new color
    if (cifContent) {
      loadCifContent(cifContent);
    }
  }, [cifContent, loadCifContent]);

  const handleBallStickColorChange = useCallback((color: string) => {
    setBallStickColor(color);
    // Reload content to apply new color
    if (cifContent) {
      loadCifContent(cifContent);
    }
  }, [cifContent, loadCifContent]);

  const handleSurfaceColorChange = useCallback((color: string) => {
    setSurfaceColor(color);
    // Reload content to apply new color
    if (cifContent) {
      loadCifContent(cifContent);
    }
  }, [cifContent, loadCifContent]);

  // Apply color scheme
  const applyColorScheme = useCallback((scheme: string) => {
    setColorScheme(scheme);
    // Reload content to apply new color scheme
    if (cifContent) {
      loadCifContent(cifContent);
    }
  }, [cifContent, loadCifContent]);

  // Apply selection preset
  const applySelectionPreset = useCallback((presetValue: string) => {
    const preset = SELECTION_PRESETS.find(p => p.value === presetValue);
    if (preset && stageRef.current) {
      setSelectedPreset(presetValue);
      // Apply selection in NGL
      stageRef.current.getComponentsByObject().forEach((component: any) => {
        component.setSelection(preset.selection);
      });
    }
  }, []);

  // Toggle measurement mode
  const toggleMeasurementMode = useCallback(() => {
    setMeasurementMode(prev => !prev);
    if (stageRef.current) {
      if (!measurementMode) {
        // Enable measurement mode
        stageRef.current.mouseControls.add('clickPick-left', (stage: any, pickingProxy: any) => {
          console.log('Measurement point:', pickingProxy.position);
          // Add measurement logic here
        });
      } else {
        // Disable measurement mode
        stageRef.current.mouseControls.remove('clickPick-left');
      }
    }
  }, [measurementMode]);

  // Toggle binding sites visualization
  const toggleBindingSites = useCallback(() => {
    setShowBindingSites(prev => !prev);
    if (stageRef.current && cifContent) {
      if (!showBindingSites) {
        // Add binding site visualization
        stageRef.current.getComponentsByObject().forEach((component: any) => {
          component.addRepresentation('surface', {
            color: 'orange',
            opacity: 0.3,
            surfaceType: 'av',
            probeRadius: 1.4,
            sele: 'cavities'
          });
        });
      } else {
        // Remove binding site visualization
        stageRef.current.getComponentsByObject().forEach((component: any) => {
          component.removeRepresentation('surface');
        });
      }
    }
  }, [showBindingSites, cifContent]);

  // Effects
  useEffect(() => {
    initializeNGL();
    return () => {
      if (stageRef.current) {
        stageRef.current.dispose();
      }
    };
  }, [initializeNGL]);

  useEffect(() => {
    if (isInitialized && cifContent) {
      loadCifContent(cifContent);
    }
  }, [isInitialized, cifContent, loadCifContent]);

  // Don't render anything if no CIF content
  if (!cifContent) {
    return <EmptyViewer height={height} className={className} state={state} />;
  }

  return (
    <div className={`relative bg-gray-900 border border-gray-700 rounded-lg overflow-hidden ${className}`} style={{ height }}>
      {/* Loading overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-gray-900/80 flex items-center justify-center z-30">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-blue-400" />
            <div className="text-sm text-gray-300">Loading structure...</div>
          </div>
        </div>
      )}

      {/* Error overlay */}
      {error && (
        <div className="absolute inset-0 bg-gray-900/80 flex items-center justify-center z-30">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 mx-auto mb-2 text-red-400" />
            <div className="text-sm font-medium mb-2 text-white">Error Loading Structure</div>
            <div className="text-xs text-gray-300">{error}</div>
          </div>
        </div>
      )}

      {/* NGL Viewer Container */}
      <div ref={containerRef} className="absolute inset-0" />

      {/* Top-right controls */}
      <div className="absolute top-4 right-4 flex gap-2 z-50">
        <Button
          variant="outline"
          size="sm"
          onClick={handleScreenshot}
          className="bg-gray-800/90 backdrop-blur-sm border-gray-600 text-white hover:bg-gray-700"
          disabled={!structureLoaded}
        >
          <Camera className="h-4 w-4 mr-2" />
          Screenshot
        </Button>
        
        <Button
          variant="outline"
          size="sm"
          onClick={handleResetView}
          className="bg-gray-800/90 backdrop-blur-sm border-gray-600 text-white hover:bg-gray-700"
          disabled={!structureLoaded}
        >
          <RotateCcw className="h-4 w-4 mr-2" />
          Reset View
        </Button>
        
        {onExpand && (
          <Button
            variant="outline"
            size="sm"
            onClick={onExpand}
            className="bg-gray-800/90 backdrop-blur-sm border-gray-600 text-white hover:bg-gray-700"
          >
            <Expand className="h-4 w-4 mr-2" />
            Expand
          </Button>
        )}
      </div>

      {/* Basic representation controls */}
      {structureLoaded && (
        <div className="absolute bottom-4 left-4 flex gap-2 z-50">
          {/* Cartoon representation with color picker */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => toggleRepresentation('cartoon')}
              className={`backdrop-blur-sm text-xs border-gray-600 ${
                representationVisibility.cartoon 
                  ? 'bg-gray-700 text-white border-gray-500 hover:bg-gray-600' 
                  : 'bg-gray-800/90 text-gray-400 hover:bg-gray-700'
              }`}
            >
              Cartoon
            </Button>
            <ColorPicker
              color={cartoonColor}
              onChange={handleCartoonColorChange}
              disabled={!representationVisibility.cartoon}
              overridden={COLOR_SCHEME_OVERRIDES[colorScheme] || false}
            />
          </div>

          {/* Ball+Stick representation with color picker */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => toggleRepresentation('ball+stick')}
              className={`backdrop-blur-sm text-xs border-gray-600 ${
                representationVisibility['ball+stick']
                  ? 'bg-gray-700 text-white border-gray-500 hover:bg-gray-600' 
                  : 'bg-gray-800/90 text-gray-400 hover:bg-gray-700'
              }`}
            >
              Ball+Stick
            </Button>
            <DisabledColorPicker title="Uses natural atomic colors" />
          </div>

          {/* Surface representation with color picker */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => toggleRepresentation('surface')}
              className={`backdrop-blur-sm text-xs border-gray-600 ${
                representationVisibility.surface
                  ? 'bg-gray-700 text-white border-gray-500 hover:bg-gray-600' 
                  : 'bg-gray-800/90 text-gray-400 hover:bg-gray-700'
              }`}
            >
              Surface
            </Button>
            <ColorPicker
              color={surfaceColor}
              onChange={handleSurfaceColorChange}
              disabled={!representationVisibility.surface}
              overridden={COLOR_SCHEME_OVERRIDES[colorScheme] || false}
            />
          </div>
          
          {/* Advanced toggle button */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="bg-gray-800/90 backdrop-blur-sm border-gray-600 text-white hover:bg-gray-700"
          >
            <Settings className="h-4 w-4 mr-1" />
            Advanced
          </Button>
        </div>
      )}

      {/* Advanced controls panel */}
      {showAdvanced && structureLoaded && (
        <div className="absolute bottom-16 left-4 z-50">
          <Card className="bg-gray-800/95 backdrop-blur-sm border-gray-600 text-white w-80">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center justify-between">
                <span>Advanced Controls</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowAdvanced(false)}
                  className="h-6 w-6 p-0 text-gray-400 hover:text-white"
                >
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Color Scheme Selection */}
              <div>
                <label className="text-xs text-gray-400 mb-2 block">Color Scheme</label>
                <Select value={colorScheme} onValueChange={applyColorScheme}>
                  <SelectTrigger className="bg-gray-700 border-gray-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-700 border-gray-600">
                    {COLOR_SCHEMES.map(scheme => (
                      <SelectItem key={scheme.value} value={scheme.value}>
                        {scheme.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Selection Presets */}
              <div>
                <label className="text-xs text-gray-400 mb-2 block">Selection Preset</label>
                <Select value={selectedPreset} onValueChange={applySelectionPreset}>
                  <SelectTrigger className="bg-gray-700 border-gray-600">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-gray-700 border-gray-600">
                    {SELECTION_PRESETS.map(preset => (
                      <SelectItem key={preset.value} value={preset.value}>
                        {preset.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Separator className="bg-gray-600" />

              {/* Color Customization */}
              <div className="space-y-3">
                <label className="text-xs text-gray-400 block">Color Customization</label>
                
                {/* Cartoon Color */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-300">Cartoon (Protein)</span>
                  <ColorPicker
                    color={cartoonColor}
                    onChange={handleCartoonColorChange}
                    disabled={!representationVisibility.cartoon}
                    overridden={COLOR_SCHEME_OVERRIDES[colorScheme] || false}
                  />
                </div>
                
                {/* Ball+Stick Color */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-300">Ball+Stick (Ligand)</span>
                  <DisabledColorPicker title="Uses natural atomic colors" />
                </div>
                
                {/* Surface Color */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-300">Surface</span>
                  <ColorPicker
                    color={surfaceColor}
                    onChange={handleSurfaceColorChange}
                    disabled={!representationVisibility.surface}
                    overridden={COLOR_SCHEME_OVERRIDES[colorScheme] || false}
                  />
                </div>
                
                                 {/* Reset Colors Button */}
                 <Button
                   variant="outline"
                   size="sm"
                   onClick={() => {
                     setCartoonColor('#4A90E2');
                     setBallStickColor('#7ED321');
                     setSurfaceColor('#F5A623');
                     // Reload content to apply reset colors
                     if (cifContent) {
                       setTimeout(() => {
                         loadCifContent(cifContent);
                       }, 100);
                     }
                   }}
                   className="text-xs bg-gray-700 border-gray-600 text-gray-300 w-full"
                 >
                   <RotateCw className="h-3 w-3 mr-2" />
                   Reset Colors
                 </Button>
              </div>

              <Separator className="bg-gray-600" />

              {/* Interactive Features */}
              <div className="space-y-2">
                <label className="text-xs text-gray-400 block">Interactive Features</label>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={toggleMeasurementMode}
                    className={`text-xs ${
                      measurementMode 
                        ? 'bg-green-600 border-green-500 text-white' 
                        : 'bg-gray-700 border-gray-600 text-gray-300'
                    }`}
                  >
                    <Ruler className="h-3 w-3 mr-1" />
                    Measure
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={toggleBindingSites}
                    className={`text-xs ${
                      showBindingSites 
                        ? 'bg-orange-600 border-orange-500 text-white' 
                        : 'bg-gray-700 border-gray-600 text-gray-300'
                    }`}
                  >
                    <Target className="h-3 w-3 mr-1" />
                    Binding Sites
                  </Button>
                </div>
              </div>

              {/* Mouse Controls Guide */}
              <div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowMouseControls(!showMouseControls)}
                  className="text-xs bg-gray-700 border-gray-600 text-gray-300 w-full"
                >
                  <Mouse className="h-3 w-3 mr-2" />
                  Mouse Controls
                  {showMouseControls ? <ChevronUp className="h-3 w-3 ml-auto" /> : <ChevronDown className="h-3 w-3 ml-auto" />}
                </Button>
                
                {showMouseControls && (
                  <div className="mt-2 p-3 bg-gray-700/50 rounded text-xs text-gray-300 space-y-1">
                    <div><strong>Left Click + Drag:</strong> Rotate</div>
                    <div><strong>Right Click + Drag:</strong> Pan</div>
                    <div><strong>Scroll Wheel:</strong> Zoom</div>
                    <div><strong>Double Click:</strong> Auto-center</div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Status overlay */}
      {structureLoaded && (
        <div className="absolute bottom-2 right-2 z-10">
          <div className="bg-background/80 backdrop-blur-sm rounded px-2 py-1">
            <div className="text-xs text-muted-foreground">
              3D Structure Loaded • Interactive Viewer Active
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MolstarViewer; 