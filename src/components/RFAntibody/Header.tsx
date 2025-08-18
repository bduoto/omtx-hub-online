import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ChevronDown, Zap, Clock, Cpu, Activity, Microscope, Target, GitCompareArrows, Search, Dna, Home, BarChart3 } from 'lucide-react';

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
    id: 'nanobody_design',
    name: 'Nanobody Design',
    description: 'Design single-domain antibodies against target proteins',
    icon: Dna,
    estimatedTime: '30-60 min',
    inputs: ['Target PDB structure', 'Hotspot residues'],
    outputs: ['Multiple nanobody designs', '3D structures', 'Binding predictions']
  },
  {
    id: 'cdr_optimization',
    name: 'CDR Optimization',
    description: 'Optimize antibody CDR loops for improved binding affinity',
    icon: Activity,
    estimatedTime: '45-90 min',
    inputs: ['Antibody structure', 'Target structure'],
    outputs: ['Optimized CDR sequences', 'Predicted affinity', 'Structural models']
  },
  {
    id: 'epitope_targeted_design',
    name: 'Epitope Targeted Design',
    description: 'Design antibodies targeting specific epitopes on protein surfaces',
    icon: Target,
    estimatedTime: '60-120 min',
    inputs: ['Target structure', 'Epitope residues', 'Framework preference'],
    outputs: ['Epitope-specific antibodies', 'Binding modes', 'Affinity predictions']
  },
  {
    id: 'antibody_de_novo_design',
    name: 'Antibody De Novo Design',
    description: 'Generate completely new antibodies against target proteins',
    icon: Microscope,
    estimatedTime: '90-180 min',
    inputs: ['Target structure', 'Design constraints', 'Framework type'],
    outputs: ['Full antibody designs', 'CDR sequences', 'Complex structures']
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
            <p className="text-gray-400">AI-Powered Antibody Design Platform</p>
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