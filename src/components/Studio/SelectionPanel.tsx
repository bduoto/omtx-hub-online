
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  MousePointer, 
  Square, 
  Circle, 
  Ruler, 
  Move3D,
  Target,
  Layers,
  Eye,
  EyeOff
} from 'lucide-react';

interface SelectionPanelProps {
  molecule: any;
}

export const SelectionPanel: React.FC<SelectionPanelProps> = ({ molecule }) => {
  const [selectionMode, setSelectionMode] = useState('atom');
  const [selectedAtoms, setSelectedAtoms] = useState([]);
  const [measurements, setMeasurements] = useState([]);

  const selectionModes = [
    { id: 'atom', name: 'Atom', icon: MousePointer },
    { id: 'residue', name: 'Residue', icon: Target },
    { id: 'chain', name: 'Chain', icon: Layers },
    { id: 'rectangle', name: 'Rectangle', icon: Square },
    { id: 'sphere', name: 'Sphere', icon: Circle },
  ];

  const measurementTools = [
    { id: 'distance', name: 'Distance', icon: Ruler, color: '#E2E756' },
    { id: 'angle', name: 'Angle', icon: Move3D, color: '#56E7A4' },
    { id: 'dihedral', name: 'Dihedral', icon: Target, color: '#5B56E7' },
  ];

  return (
    <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white">Selection & Tools</h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        <Tabs defaultValue="selection" className="h-full">
          <TabsList className="grid w-full grid-cols-2 bg-gray-700 m-2">
            <TabsTrigger value="selection" className="text-xs">Selection</TabsTrigger>
            <TabsTrigger value="measurements" className="text-xs">Measure</TabsTrigger>
          </TabsList>

          <TabsContent value="selection" className="p-4 space-y-4">
            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white">Selection Mode</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {selectionModes.map((mode) => (
                  <Button
                    key={mode.id}
                    size="sm"
                    variant={selectionMode === mode.id ? "default" : "ghost"}
                    className={`w-full justify-start ${
                      selectionMode === mode.id 
                        ? "bg-blue-600 text-white" 
                        : "text-gray-300 hover:text-white"
                    }`}
                    onClick={() => setSelectionMode(mode.id)}
                  >
                    <mode.icon className="w-4 h-4 mr-2" />
                    {mode.name}
                  </Button>
                ))}
              </CardContent>
            </Card>

            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white">Quick Select</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Input
                  placeholder="Select by residue (e.g. ALA)"
                  className="bg-gray-600 border-gray-500 text-white placeholder:text-gray-400"
                />
                <Input
                  placeholder="Select by chain (e.g. A)"
                  className="bg-gray-600 border-gray-500 text-white placeholder:text-gray-400"
                />
                <div className="flex space-x-2">
                  <Button size="sm" variant="outline" className="flex-1">
                    Select All
                  </Button>
                  <Button size="sm" variant="outline" className="flex-1">
                    Clear
                  </Button>
                </div>
              </CardContent>
            </Card>

            {selectedAtoms.length > 0 && (
              <Card className="bg-gray-700 border-gray-600">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-white">
                    Selected ({selectedAtoms.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex space-x-2">
                    <Button size="sm" variant="ghost" className="text-green-400">
                      <Eye className="w-4 h-4 mr-1" />
                      Show
                    </Button>
                    <Button size="sm" variant="ghost" className="text-red-400">
                      <EyeOff className="w-4 h-4 mr-1" />
                      Hide
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="measurements" className="p-4 space-y-4">
            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white">Measurement Tools</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {measurementTools.map((tool) => (
                  <Button
                    key={tool.id}
                    size="sm"
                    variant="ghost"
                    className="w-full justify-start text-gray-300 hover:text-white"
                    style={{ color: tool.color }}
                  >
                    <tool.icon className="w-4 h-4 mr-2" />
                    {tool.name}
                  </Button>
                ))}
              </CardContent>
            </Card>

            {measurements.length > 0 && (
              <Card className="bg-gray-700 border-gray-600">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-white">Measurements</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm text-gray-300">
                    <div>Distance: 2.34 Å</div>
                    <div>Angle: 109.5°</div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};
