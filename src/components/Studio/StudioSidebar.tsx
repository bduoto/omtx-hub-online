import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Upload, Search, Folder, File, Atom, Database, Download } from 'lucide-react';

interface StudioSidebarProps {
  onMoleculeSelect: (molecule: any) => void;
  selectedMolecule: any;
}

const mockMolecules = [
  { id: 1, name: 'Caffeine', formula: 'C8H10N4O2', type: 'pdb', size: '2.4 KB' },
  { id: 2, name: 'Aspirin', formula: 'C9H8O4', type: 'mol2', size: '1.8 KB' },
  { id: 3, name: 'Glucose', formula: 'C6H12O6', type: 'xyz', size: '1.2 KB' },
  { id: 4, name: 'DNA Helix', formula: 'Complex', type: 'pdb', size: '45.2 KB' },
];

export const StudioSidebar: React.FC<StudioSidebarProps> = ({ 
  onMoleculeSelect, 
  selectedMolecule 
}) => {
  const [searchQuery, setSearchQuery] = useState('');

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      console.log('Uploading files:', files);
      // Handle file upload logic here
    }
  };

  const filteredMolecules = mockMolecules.filter(mol =>
    mol.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    mol.formula.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="w-80 bg-gray-800 border-r border-gray-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-xl font-bold text-white mb-4">Molecular Studio</h2>
        
        {/* Upload Button */}
        <div className="mb-4">
          <input
            type="file"
            id="file-upload"
            multiple
            accept=".pdb,.mol,.mol2,.xyz,.sdf,.cif,.gro,.xtc,.trr"
            onChange={handleFileUpload}
            className="hidden"
          />
          <label htmlFor="file-upload">
            <Button 
              className="w-full" 
              style={{ backgroundColor: '#E2E756', color: '#000' }}
              asChild
            >
              <span className="cursor-pointer flex items-center justify-center">
                <Upload className="w-4 h-4 mr-2" />
                Upload Structure
              </span>
            </Button>
          </label>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            placeholder="Search molecules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-gray-700 border-gray-600 text-white placeholder:text-gray-400"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="library" className="h-full flex flex-col">
          <TabsList className="grid w-full grid-cols-2 bg-gray-700 m-2">
            <TabsTrigger value="library" className="text-gray-300">Library</TabsTrigger>
            <TabsTrigger value="recent" className="text-gray-300">Recent</TabsTrigger>
          </TabsList>
          
          <TabsContent value="library" className="flex-1 overflow-y-auto px-2">
            <div className="space-y-2">
              {filteredMolecules.map((molecule) => (
                <Card
                  key={molecule.id}
                  className={`cursor-pointer transition-colors bg-gray-700 border-gray-600 hover:bg-gray-600 ${
                    selectedMolecule?.id === molecule.id ? 'ring-2' : ''
                  }`}
                  style={{ 
                    borderColor: selectedMolecule?.id === molecule.id ? '#56E7A4' : undefined 
                  }}
                  onClick={() => onMoleculeSelect(molecule)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-start space-x-3">
                      <div className="p-2 rounded" style={{ backgroundColor: '#5B56E7' }}>
                        <Atom className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-white truncate">
                          {molecule.name}
                        </h4>
                        <p className="text-xs text-gray-400 truncate">
                          {molecule.formula}
                        </p>
                        <div className="flex justify-between items-center mt-1">
                          <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: '#E7569A', color: '#fff' }}>
                            {molecule.type.toUpperCase()}
                          </span>
                          <span className="text-xs text-gray-500">{molecule.size}</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>
          
          <TabsContent value="recent" className="flex-1 overflow-y-auto px-2">
            <div className="text-center text-gray-400 mt-8">
              <File className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No recent files</p>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-700">
        <div className="text-xs text-gray-400 space-y-1">
          <div>Supported formats:</div>
          <div>PDB, MOL, MOL2, XYZ, SDF, CIF, GRO, XTC, TRR</div>
        </div>
      </div>
    </div>
  );
};
