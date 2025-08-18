
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Filter, X } from 'lucide-react';

const categories = [
  'Protein', 'Antibody', 'Enzyme', 'Peptide', 'Small Molecule', 'CryoEM'
];

const tags = [
  'Structure Prediction', 'Protein Design', 'Antibody Design', 'Developability',
  'Protein Ligand Docking', 'Protein Protein Docking', 'Inverse Folding',
  'Molecular Dynamics', 'Binder Design', 'Protein Language Models',
  'Point Mutations', 'High Throughput', 'Experimental Data',
  'Generate Small Molecules', 'Finetuning and Active Learning', 'Utilities'
];

export const FilterPopover = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const toggleCategory = (category: string) => {
    setSelectedCategories(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  const toggleTag = (tag: string) => {
    setSelectedTags(prev => 
      prev.includes(tag) 
        ? prev.filter(t => t !== tag)
        : [...prev, tag]
    );
  };

  const clearAllFilters = () => {
    setSelectedCategories([]);
    setSelectedTags([]);
  };

  return (
    <>
      <Button 
        onClick={() => setIsOpen(!isOpen)}
        className="bg-[#E2E756] hover:bg-[#C4C93A] text-gray-900 font-medium"
      >
        <Filter className="h-4 w-4 mr-2" />
        Filters
      </Button>
      
      {isOpen && (
        <div className="col-span-full mt-4 p-6 bg-gray-800 border border-gray-600 rounded-lg shadow-lg">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-lg font-semibold text-white">Filters</h2>
            <div className="flex gap-2">
              <Button
                onClick={clearAllFilters}
                className="bg-[#E2E756] hover:bg-[#C4C93A] text-gray-900 font-medium text-xs"
                size="sm"
              >
                Clear All
              </Button>
              <Button
                onClick={() => setIsOpen(false)}
                className="bg-[#E2E756] hover:bg-[#C4C93A] text-gray-900 font-medium text-xs"
                size="sm"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          </div>
          
          <div className="space-y-6">
            <div>
              <h3 className="text-sm font-medium text-white mb-4">Filter by categories:</h3>
              <div className="flex flex-wrap gap-2">
                {categories.map((category) => (
                  <Button
                    key={category}
                    onClick={() => toggleCategory(category)}
                    className={`text-xs transition-colors ${
                      selectedCategories.includes(category)
                        ? 'bg-[#E2E756] text-gray-900 hover:bg-[#C4C93A]'
                        : 'bg-[#E2E756] text-gray-900 hover:bg-[#C4C93A] opacity-50'
                    }`}
                  >
                    {category}
                  </Button>
                ))}
              </div>
            </div>
            
            <div>
              <h3 className="text-sm font-medium text-white mb-4">Filter by tags:</h3>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <Button
                    key={tag}
                    onClick={() => toggleTag(tag)}
                    className={`text-xs transition-colors ${
                      selectedTags.includes(tag)
                        ? 'bg-[#E2E756] text-gray-900 hover:bg-[#C4C93A]'
                        : 'bg-[#E2E756] text-gray-900 hover:bg-[#C4C93A] opacity-50'
                    }`}
                  >
                    {tag}
                  </Button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
