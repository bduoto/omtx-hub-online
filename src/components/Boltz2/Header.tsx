import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ChevronDown, Zap, Clock, Cpu, Activity, Microscope, Target, GitCompareArrows, Search, Dna, Home, BarChart3, Database } from 'lucide-react';

export interface PredictionTask {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  estimatedTime: string;
  inputs: string[];
  outputs: string[];
}

export const PREDICTION_TASKS: PredictionTask[] = [
  {
    id: 'protein_ligand_binding',
    name: 'Protein-Ligand Binding',
    description: 'Predict binding affinity and generate protein-ligand complex structures',
    icon: Target,
    estimatedTime: '10-30 min',
    inputs: ['Protein sequence', 'Ligand SMILES'],
    outputs: ['Binding affinity', '3D structure', 'Confidence scores']
  },
  {
    id: 'protein_structure',
    name: 'Protein Structure Prediction',
    description: 'Predict 3D protein structure from amino acid sequence',
    icon: Dna,
    estimatedTime: '5-60 min',
    inputs: ['Protein sequence'],
    outputs: ['3D structure', 'Confidence scores', 'Quality metrics']
  },
  {
    id: 'protein_complex',
    name: 'Protein Complex Prediction',
    description: 'Predict multi-subunit protein complex structures and interactions',
    icon: Activity,
    estimatedTime: '20-90 min',
    inputs: ['Multiple protein sequences'],
    outputs: ['Complex structure', 'Interface analysis', 'Binding strength']
  },
  {
    id: 'binding_site_prediction',
    name: 'Binding Site Prediction',
    description: 'Identify potential drug binding sites and cavities in protein structures',
    icon: Search,
    estimatedTime: '5-15 min',
    inputs: ['Protein structure (PDB)'],
    outputs: ['Binding sites', 'Cavity analysis', 'Druggability scores']
  },
  {
    id: 'variant_comparison',
    name: 'Protein Variant Comparison',
    description: 'Compare effects of mutations on protein structure and function',
    icon: GitCompareArrows,
    estimatedTime: '15-45 min',
    inputs: ['Reference sequence', 'Variant sequences'],
    outputs: ['Structural changes', 'Stability analysis', 'Functional impact']
  },
  {
    id: 'drug_discovery',
    name: 'Drug Discovery Screening',
    description: 'Screen compound libraries for potential drug candidates',
    icon: Microscope,
    estimatedTime: '30-180 min',
    inputs: ['Target protein', 'Compound library'],
    outputs: ['Hit compounds', 'Binding predictions', 'ADMET properties']
  },
  {
    id: 'batch_protein_ligand_screening',
    name: 'Batch Protein-Ligand Screening',
    description: 'Screen a protein against multiple ligands (up to 100) with comprehensive results',
    icon: Database,
    estimatedTime: '30-500 min',
    inputs: ['Protein sequence', 'Ligand CSV file (up to 100)'],
    outputs: ['Batch affinity results', 'Structure files ZIP', 'Confidence scores', 'Summary report']
  }
];

interface HeaderProps {
  selectedTask: string;
  onTaskChange: (taskId: string) => void;
  readonly?: boolean;
}

const Header: React.FC<HeaderProps> = ({ selectedTask, onTaskChange, readonly = false }) => {
  const navigate = useNavigate();
  const currentTask = PREDICTION_TASKS.find(task => task.id === selectedTask) || PREDICTION_TASKS[0];
  
  const getTimeColor = (timeString: string) => {
    // Extract the maximum time from the range (e.g., "10-30 min" -> 30)
    const numbers = timeString.match(/\d+/g);
    if (!numbers) return 'bg-gray-500/20 text-gray-400 border-gray-500/30';
    
    const maxTime = Math.max(...numbers.map(Number));
    
    if (maxTime <= 30) {
      return 'bg-green-500/20 text-green-400 border-green-500/30';
    } else if (maxTime <= 60) {
      return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
    } else {
      return 'bg-red-500/20 text-red-400 border-red-500/30';
    }
  };

  const handleDashboardClick = () => {
    navigate('/');
  };

  const handleMyResultsClick = () => {
    navigate('/my-results');
  };

  return (
    <div className="space-y-6">
      {/* Main Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <currentTask.icon className="h-6 w-6 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">{currentTask.name}</h1>
            <p className="text-gray-400">AI-Powered Molecular Modeling Platform</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-3">
          <Button 
            variant="outline" 
            size="sm"
            onClick={handleDashboardClick}
            className="bg-gray-800/50 border-gray-600 text-gray-300 hover:bg-gray-700/50 hover:text-white"
          >
            <Home className="h-4 w-4 mr-2" />
            Home
          </Button>
          <Button 
            variant="outline" 
            size="sm"
            onClick={handleMyResultsClick}
            className="bg-gray-800/50 border-gray-600 text-gray-300 hover:bg-gray-700/50 hover:text-white"
          >
            <BarChart3 className="h-4 w-4 mr-2" />
            My Results
          </Button>
        </div>
      </div>

      {/* Task Selection */}
      <Card className="bg-gray-800/50 border-gray-700">
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">
              {readonly ? 'Job Task Type' : 'Select Prediction Task'}
            </h2>
            {!readonly ? (
              <Select value={selectedTask} onValueChange={onTaskChange}>
                <SelectTrigger className="w-80 bg-gray-700 border-gray-600 text-white">
                  <SelectValue placeholder="Choose a prediction task" />
                </SelectTrigger>
                <SelectContent className="bg-gray-700 border-gray-600">
                  {PREDICTION_TASKS.map((task) => (
                    <SelectItem key={task.id} value={task.id} className="text-white hover:bg-gray-600">
                      <div className="flex items-center space-x-3">
                        <task.icon className="h-4 w-4" />
                        <span>{task.name}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <Badge variant="secondary" className="bg-blue-500/20 text-blue-400 border-blue-500/30">
                <currentTask.icon className="h-3 w-3 mr-1" />
                {currentTask.name}
              </Badge>
            )}
          </div>

          {/* Current Task Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-white font-medium mb-2">{currentTask.name}</h3>
              <p className="text-gray-400 text-sm mb-4">{currentTask.description}</p>
              
              <div className="flex items-center space-x-4 text-sm">
                <Badge className={`${getTimeColor(currentTask.estimatedTime)} flex items-center space-x-1`}>
                  <Clock className="h-3 w-3" />
                  <span>{currentTask.estimatedTime}</span>
                </Badge>
              </div>
            </div>

            <div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-white mb-2">Inputs</h4>
                  <ul className="text-sm text-gray-400 space-y-1">
                    {currentTask.inputs.map((input, index) => (
                      <li key={index} className="flex items-center space-x-2">
                        <div className="w-1 h-1 bg-blue-400 rounded-full"></div>
                        <span>{input}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                
                <div>
                  <h4 className="text-sm font-medium text-white mb-2">Outputs</h4>
                  <ul className="text-sm text-gray-400 space-y-1">
                    {currentTask.outputs.map((output, index) => (
                      <li key={index} className="flex items-center space-x-2">
                        <div className="w-1 h-1 bg-green-400 rounded-full"></div>
                        <span>{output}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Header;