
import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Search, 
  Target, 
  ChevronLeft, 
  ChevronRight,
  Maximize,
  Download
} from 'lucide-react';

interface SequenceViewerProps {
  molecule: any;
  onResidueSelect: (residue: any) => void;
}

export const SequenceViewer: React.FC<SequenceViewerProps> = ({
  molecule,
  onResidueSelect
}) => {
  const [selectedResidue, setSelectedResidue] = useState(null);
  const [showSecondaryStructure, setShowSecondaryStructure] = useState(true);

  // Mock sequence data
  const sequences = [
    {
      chain: 'A',
      sequence: 'MKWVTFISLLFLFSSAYSRGVFRRDAHKSEVAHRFKDLGEENFKALVLIAFAQYLQQCPFEDHVKLVNEVTEFAKTCVADESAENCDKSLHTLFGDKLCTVATLRETYGEMADCCAKQEPERNECFLQHKDDNPNLPRLVRPEVDVMCTAFHDNEETFLKKYLYEIARRHPYFYAPELLFFAKRYKAAFTECCQAADKAACLLPKLDELRDEGKASSAKQRLKCASLQKFGERAFKAWAVARLSQRFPKAEFAEVSKLVT',
      secondary: 'CCCCCCCCCCCCCCCCHHHHHHHHHHHHHHHHCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCHHHHHHHHHHHHHHHHHHHHHHHCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC'
    }
  ];

  const getResidueColor = (residue: string, index: number) => {
    const colors = {
      'A': '#C8C8C8', 'V': '#C8C8C8', 'L': '#C8C8C8', 'I': '#C8C8C8', 'M': '#C8C8C8', // Hydrophobic
      'F': '#3232AA', 'W': '#3232AA', 'Y': '#3232AA', // Aromatic
      'S': '#15A015', 'T': '#15A015', 'N': '#15A015', 'Q': '#15A015', // Polar
      'R': '#E60A0A', 'K': '#E60A0A', 'H': '#8282D2', // Positive
      'D': '#E60A0A', 'E': '#E60A0A', // Negative
      'C': '#E6E600', // Cysteine
      'G': '#EBEBEB', 'P': '#DC9682' // Special
    };
    return colors[residue] || '#FFFFFF';
  };

  const getSecondaryStructureSymbol = (ss: string) => {
    switch (ss) {
      case 'H': return '━'; // Helix
      case 'E': return '→'; // Sheet
      default: return '·'; // Coil
    }
  };

  return (
    <div className="h-64 bg-gray-800 border-t border-gray-700">
      <Card className="h-full bg-gray-700 border-gray-600 rounded-none">
        <CardHeader className="pb-2 px-4 py-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm text-white flex items-center">
              <Target className="w-4 h-4 mr-2" style={{ color: '#E2E756' }} />
              Sequence Viewer
            </CardTitle>
            <div className="flex items-center space-x-2">
              <Button size="sm" variant="ghost" className="text-gray-400 hover:text-white p-1">
                <Search className="w-3 h-3" />
              </Button>
              <Button size="sm" variant="ghost" className="text-gray-400 hover:text-white p-1">
                <Maximize className="w-3 h-3" />
              </Button>
              <Button size="sm" variant="ghost" className="text-gray-400 hover:text-white p-1">
                <Download className="w-3 h-3" />
              </Button>
            </div>
          </div>
        </CardHeader>
        
        <CardContent className="p-2 h-full">
          <ScrollArea className="h-full">
            {sequences.map((seq, chainIndex) => (
              <div key={seq.chain} className="mb-4">
                <div className="flex items-center mb-2">
                  <span className="text-xs text-gray-400 w-12">Chain {seq.chain}</span>
                  <div className="flex-1 h-px bg-gray-600"></div>
                </div>
                
                {/* Secondary Structure Row */}
                {showSecondaryStructure && (
                  <div className="mb-1">
                    <span className="text-xs text-gray-500 w-12 inline-block">SS:</span>
                    <div className="font-mono text-xs inline-flex">
                      {seq.secondary.split('').map((ss, i) => (
                        <span
                          key={i}
                          className="w-3 text-center"
                          style={{ 
                            color: ss === 'H' ? '#E7569A' : ss === 'E' ? '#56E7A4' : '#666'
                          }}
                        >
                          {getSecondaryStructureSymbol(ss)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Sequence Row */}
                <div>
                  <span className="text-xs text-gray-500 w-12 inline-block">Seq:</span>
                  <div className="font-mono text-xs inline-flex">
                    {seq.sequence.split('').map((residue, i) => (
                      <span
                        key={i}
                        className="w-3 text-center cursor-pointer hover:bg-gray-600 rounded"
                        style={{ color: getResidueColor(residue, i) }}
                        onClick={() => {
                          setSelectedResidue({ chain: seq.chain, index: i, residue });
                          onResidueSelect({ chain: seq.chain, index: i, residue });
                        }}
                        title={`${residue}${i + 1}`}
                      >
                        {residue}
                      </span>
                    ))}
                  </div>
                </div>
                
                {/* Numbering Row */}
                <div>
                  <span className="text-xs text-gray-500 w-12 inline-block">Num:</span>
                  <div className="font-mono text-xs inline-flex">
                    {seq.sequence.split('').map((_, i) => (
                      <span
                        key={i}
                        className="w-3 text-center text-gray-500"
                      >
                        {(i + 1) % 10 === 0 ? (i + 1) / 10 : ''}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
};
