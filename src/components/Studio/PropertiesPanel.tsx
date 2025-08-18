
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { 
  Atom, 
  Ruler, 
  Activity, 
  BarChart3, 
  Eye, 
  Palette,
  Download,
  Calculator
} from 'lucide-react';

interface PropertiesPanelProps {
  molecule: any;
  viewMode: string;
}

export const PropertiesPanel: React.FC<PropertiesPanelProps> = ({
  molecule,
  viewMode
}) => {
  const [opacity, setOpacity] = useState([100]);
  const [bondRadius, setBondRadius] = useState([50]);
  const [atomSize, setAtomSize] = useState([75]);

  const mockProperties = {
    atoms: 24,
    bonds: 26,
    mass: '194.19 g/mol',
    volume: '143.2 Ų',
    surface: '189.4 Ų',
    dipole: '1.85 D',
    charge: '0',
    energy: '-2847.3 kcal/mol'
  };

  return (
    <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white">Properties</h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        <Tabs defaultValue="structure" className="h-full">
          <TabsList className="grid w-full grid-cols-3 bg-gray-700 m-2">
            <TabsTrigger value="structure" className="text-xs">Structure</TabsTrigger>
            <TabsTrigger value="visual" className="text-xs">Visual</TabsTrigger>
            <TabsTrigger value="analysis" className="text-xs">Analysis</TabsTrigger>
          </TabsList>

          <TabsContent value="structure" className="p-4 space-y-4">
            {molecule ? (
              <>
                <Card className="bg-gray-700 border-gray-600">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-white flex items-center">
                      <Atom className="w-4 h-4 mr-2" style={{ color: '#E2E756' }} />
                      Basic Properties
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Atoms:</span>
                      <span className="text-white">{mockProperties.atoms}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Bonds:</span>
                      <span className="text-white">{mockProperties.bonds}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Mass:</span>
                      <span className="text-white">{mockProperties.mass}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Charge:</span>
                      <span className="text-white">{mockProperties.charge}</span>
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-gray-700 border-gray-600">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm text-white flex items-center">
                      <Ruler className="w-4 h-4 mr-2" style={{ color: '#56E7A4' }} />
                      Geometry
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Volume:</span>
                      <span className="text-white">{mockProperties.volume}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Surface:</span>
                      <span className="text-white">{mockProperties.surface}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-400">Dipole:</span>
                      <span className="text-white">{mockProperties.dipole}</span>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <div className="text-center text-gray-400 mt-8">
                <Atom className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No molecule selected</p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="visual" className="p-4 space-y-4">
            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white flex items-center">
                  <Eye className="w-4 h-4 mr-2" style={{ color: '#5B56E7' }} />
                  Display Settings
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm text-gray-400">Opacity</label>
                    <span className="text-sm text-white">{opacity[0]}%</span>
                  </div>
                  <Slider
                    value={opacity}
                    onValueChange={setOpacity}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>

                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm text-gray-400">Atom Size</label>
                    <span className="text-sm text-white">{atomSize[0]}%</span>
                  </div>
                  <Slider
                    value={atomSize}
                    onValueChange={setAtomSize}
                    max={200}
                    step={1}
                    className="w-full"
                  />
                </div>

                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm text-gray-400">Bond Radius</label>
                    <span className="text-sm text-white">{bondRadius[0]}%</span>
                  </div>
                  <Slider
                    value={bondRadius}
                    onValueChange={setBondRadius}
                    max={200}
                    step={1}
                    className="w-full"
                  />
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white flex items-center">
                  <Palette className="w-4 h-4 mr-2" style={{ color: '#E7569A' }} />
                  Color Scheme
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-2">
                  <div className="w-8 h-8 rounded border-2 border-gray-600" style={{ backgroundColor: '#E2E756' }}></div>
                  <div className="w-8 h-8 rounded border-2 border-gray-600" style={{ backgroundColor: '#56E7A4' }}></div>
                  <div className="w-8 h-8 rounded border-2 border-gray-600" style={{ backgroundColor: '#5B56E7' }}></div>
                  <div className="w-8 h-8 rounded border-2 border-gray-600" style={{ backgroundColor: '#E7569A' }}></div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analysis" className="p-4 space-y-4">
            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white flex items-center">
                  <Calculator className="w-4 h-4 mr-2" style={{ color: '#E2E756' }} />
                  Calculations
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button 
                  size="sm" 
                  className="w-full justify-start" 
                  variant="ghost"
                  style={{ color: '#56E7A4' }}
                >
                  <Activity className="w-4 h-4 mr-2" />
                  Energy Minimization
                </Button>
                <Button 
                  size="sm" 
                  className="w-full justify-start" 
                  variant="ghost"
                  style={{ color: '#5B56E7' }}
                >
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Molecular Dynamics
                </Button>
                <Button 
                  size="sm" 
                  className="w-full justify-start" 
                  variant="ghost"
                  style={{ color: '#E7569A' }}
                >
                  <Ruler className="w-4 h-4 mr-2" />
                  Distance Analysis
                </Button>
              </CardContent>
            </Card>

            {molecule && (
              <Card className="bg-gray-700 border-gray-600">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-white">Energy</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-mono text-white">
                    {mockProperties.energy}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>

      <div className="p-4 border-t border-gray-700">
        <Button 
          size="sm" 
          className="w-full" 
          style={{ backgroundColor: '#E2E756', color: '#000' }}
        >
          <Download className="w-4 h-4 mr-2" />
          Export Data
        </Button>
      </div>
    </div>
  );
};
