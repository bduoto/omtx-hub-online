
import React from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { X } from 'lucide-react';

interface FilterPanelProps {
  isOpen: boolean;
  onClose: () => void;
  selectedTags: string[];
  onTagToggle: (tag: string) => void;
  onResetFilters: () => void;
}

const tags = [
  'Structure Prediction',
  'Protein Design', 
  'Antibody Design',
  'Developability',
  'Protein Ligand Docking',
  'Protein Protein Docking',
  'Inverse Folding',
  'Molecular Dynamics',
  'Binder Design',
  'Protein Language Models',
  'Point Mutations',
  'High Throughput',
  'Experimental Data',
  'Generate Small Molecules',
  'Finetuning and Active Learning',
  'Utilities'
];

export const FilterPanel: React.FC<FilterPanelProps> = ({
  isOpen,
  onClose,
  selectedTags,
  onTagToggle,
  onResetFilters
}) => {
  return (
    <div 
      className={`overflow-hidden transition-all duration-300 ease-in-out ${
        isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
      }`}
    >
      <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-white">Filter Options</h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">Category</label>
            <select className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white">
              <option value="">All Categories</option>
              <option value="protein">Protein</option>
              <option value="antibody">Antibody</option>
              <option value="enzyme">Enzyme</option>
              <option value="peptide">Peptide</option>
              <option value="small-molecule">Small Molecule</option>
              <option value="cryoem">CryoEM</option>
            </select>
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">Author</label>
            <Input 
              placeholder="Filter by author..."
              className="bg-gray-700 border-gray-600 text-white"
            />
          </div>
          
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-300">Bookmarked</label>
            <select className="w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-white">
              <option value="">All Models</option>
              <option value="bookmarked">Bookmarked Only</option>
              <option value="not-bookmarked">Not Bookmarked</option>
            </select>
          </div>
        </div>

        <div className="space-y-3">
          <label className="text-sm font-medium text-gray-300">Filter by tags:</label>
          <div className="flex flex-wrap gap-2">
            {tags.map((tag) => (
              <button
                key={tag}
                onClick={() => onTagToggle(tag)}
                className={`px-4 py-2 rounded-full border text-sm font-medium transition-colors ${
                  selectedTags.includes(tag)
                    ? 'bg-[#E2E756] border-[#E2E756] text-gray-900'
                    : 'bg-transparent border-gray-500 text-gray-300 hover:border-gray-400 hover:text-white'
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex gap-2 pt-4">
          <Button 
            variant="outline" 
            className="border-gray-600 text-white hover:bg-gray-700"
            onClick={onResetFilters}
          >
            Reset Filters
          </Button>
          <Button className="bg-[#E2E756] hover:bg-[#C4C93A] text-gray-900">
            Apply Filters
          </Button>
        </div>
      </div>
    </div>
  );
};
