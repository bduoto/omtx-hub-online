
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Camera, 
  Image, 
  Video, 
  Settings, 
  Layers,
  Sun,
  Palette,
  Download
} from 'lucide-react';

interface RenderingPanelProps {
  molecule: any;
}

export const RenderingPanel: React.FC<RenderingPanelProps> = ({ molecule }) => {
  const [rayTracingEnabled, setRayTracingEnabled] = useState(false);
  const [ambientOcclusion, setAmbientOcclusion] = useState([50]);
  const [shadowQuality, setShadowQuality] = useState([75]);
  const [antiAliasing, setAntiAliasing] = useState([100]);

  const renderPresets = [
    { name: 'Publication', quality: 'High', time: '~5min' },
    { name: 'Presentation', quality: 'Medium', time: '~2min' },
    { name: 'Preview', quality: 'Low', time: '~30s' },
  ];

  const outputFormats = [
    { name: 'PNG', ext: '.png', desc: 'High quality raster' },
    { name: 'JPEG', ext: '.jpg', desc: 'Compressed raster' },
    { name: 'SVG', ext: '.svg', desc: 'Vector graphics' },
    { name: 'PDF', ext: '.pdf', desc: 'Publication ready' },
    { name: 'MP4', ext: '.mp4', desc: 'Video animation' },
  ];

  return (
    <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col">
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white flex items-center">
          <Camera className="w-5 h-5 mr-2" style={{ color: '#E2E756' }} />
          Rendering
        </h3>
      </div>

      <div className="flex-1 overflow-y-auto">
        <Tabs defaultValue="quality" className="h-full">
          <TabsList className="grid w-full grid-cols-3 bg-gray-700 m-2">
            <TabsTrigger value="quality" className="text-xs">Quality</TabsTrigger>
            <TabsTrigger value="lighting" className="text-xs">Lighting</TabsTrigger>
            <TabsTrigger value="export" className="text-xs">Export</TabsTrigger>
          </TabsList>

          <TabsContent value="quality" className="p-4 space-y-4">
            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white">Render Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm text-gray-400">Anti-Aliasing</label>
                    <span className="text-sm text-white">{antiAliasing[0]}%</span>
                  </div>
                  <Slider
                    value={antiAliasing}
                    onValueChange={setAntiAliasing}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>

                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm text-gray-400">Shadow Quality</label>
                    <span className="text-sm text-white">{shadowQuality[0]}%</span>
                  </div>
                  <Slider
                    value={shadowQuality}
                    onValueChange={setShadowQuality}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Ray Tracing</span>
                  <Button
                    size="sm"
                    variant={rayTracingEnabled ? "default" : "outline"}
                    onClick={() => setRayTracingEnabled(!rayTracingEnabled)}
                    style={rayTracingEnabled ? { backgroundColor: '#56E7A4', color: '#000' } : {}}
                  >
                    {rayTracingEnabled ? 'On' : 'Off'}
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white">Presets</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {renderPresets.map((preset, index) => (
                  <Button
                    key={index}
                    size="sm"
                    variant="ghost"
                    className="w-full justify-between text-gray-300 hover:text-white hover:bg-gray-600"
                  >
                    <span>{preset.name}</span>
                    <span className="text-xs text-gray-500">{preset.time}</span>
                  </Button>
                ))}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="lighting" className="p-4 space-y-4">
            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white flex items-center">
                  <Sun className="w-4 h-4 mr-2" style={{ color: '#E2E756' }} />
                  Lighting Setup
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <label className="text-sm text-gray-400">Ambient Occlusion</label>
                    <span className="text-sm text-white">{ambientOcclusion[0]}%</span>
                  </div>
                  <Slider
                    value={ambientOcclusion}
                    onValueChange={setAmbientOcclusion}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm text-gray-400">Environment</label>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="w-full h-8 bg-gradient-to-b from-blue-400 to-blue-600 rounded border cursor-pointer"></div>
                    <div className="w-full h-8 bg-gradient-to-b from-gray-300 to-gray-500 rounded border cursor-pointer"></div>
                    <div className="w-full h-8 bg-gradient-to-b from-orange-300 to-orange-500 rounded border cursor-pointer"></div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="export" className="p-4 space-y-4">
            <Card className="bg-gray-700 border-gray-600">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-white flex items-center">
                  <Download className="w-4 h-4 mr-2" style={{ color: '#56E7A4' }} />
                  Export Options
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {outputFormats.map((format, index) => (
                  <Button
                    key={index}
                    size="sm"
                    variant="ghost"
                    className="w-full justify-between text-gray-300 hover:text-white hover:bg-gray-600"
                  >
                    <div className="text-left">
                      <div className="font-medium">{format.name}</div>
                      <div className="text-xs text-gray-500">{format.desc}</div>
                    </div>
                    <span className="text-xs text-gray-400">{format.ext}</span>
                  </Button>
                ))}
              </CardContent>
            </Card>

            <Button 
              className="w-full" 
              style={{ backgroundColor: '#E2E756', color: '#000' }}
            >
              <Camera className="w-4 h-4 mr-2" />
              Render Image
            </Button>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};
