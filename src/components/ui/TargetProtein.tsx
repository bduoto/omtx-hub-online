import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

interface TargetProteinProps {
  proteinName: string;
  onProteinNameChange: (name: string) => void;
  proteinSequence: string;
  onProteinSequenceChange: (sequence: string) => void;
  isViewMode?: boolean;
  isReadOnly?: boolean;
  showProteinName?: boolean;
}

export const TargetProtein: React.FC<TargetProteinProps> = ({
  proteinName,
  onProteinNameChange,
  proteinSequence,
  onProteinSequenceChange,
  isViewMode = false,
  isReadOnly = false,
  showProteinName = true
}) => {
  return (
    <Card className="bg-gray-800/50 border-gray-700">
      <CardHeader>
        <CardTitle className="text-white text-sm">Target Protein</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {showProteinName && (
          <div>
            <Label htmlFor="protein-name" className="text-sm font-medium text-gray-300">
              Protein Name
            </Label>
            <Input
              id="protein-name"
              placeholder="e.g., Carbonic Anhydrase II"
              value={proteinName}
              onChange={(e) => !isViewMode && !isReadOnly && onProteinNameChange(e.target.value)}
              className="mt-1 bg-gray-800/50 border-gray-700 text-white"
              readOnly={isViewMode || isReadOnly}
            />
          </div>
        )}

        <div>
          <Label htmlFor="protein-sequence" className="text-sm font-medium text-gray-300">
            Protein Sequence
          </Label>
          <Textarea
            id="protein-sequence"
            placeholder="Enter protein sequence in FASTA format"
            value={proteinSequence}
            onChange={(e) => !isViewMode && !isReadOnly && onProteinSequenceChange(e.target.value.toUpperCase())}
            className="mt-1 bg-gray-800/50 border-gray-700 text-white min-h-[100px] font-mono text-sm"
            rows={4}
            readOnly={isViewMode || isReadOnly}
          />
          {proteinSequence && (
            <div className="mt-1 text-xs text-gray-400">
              Length: {proteinSequence.length} residues
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};