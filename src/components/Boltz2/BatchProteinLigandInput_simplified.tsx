/**
 * Simplified Batch Protein-Ligand Input Component
 * 
 * Uses the new Cloud Run Native API with no authentication required.
 * Streamlined for Boltz-2 batch predictions with company API gateway integration.
 */

import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Upload, 
  X, 
  FileText, 
  Loader2, 
  Play,
  AlertCircle,
  CheckCircle,
  Database,
  Download
} from 'lucide-react';

import { jobStore } from '../../stores/jobStore_simplified';

interface LigandData {
  name: string;
  smiles: string;
}

interface BatchProteinLigandInputProps {
  onPredictionStart: () => void;
  onPredictionComplete: (result: any) => void;
  onPredictionError: (error: string) => void;
  isViewMode?: boolean;
}

// Generate random job name
const generateRandomJobName = () => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < 8; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return `batch_${result}`;
};

export const BatchProteinLigandInputSimplified: React.FC<BatchProteinLigandInputProps> = ({
  onPredictionStart,
  onPredictionComplete,
  onPredictionError,
  isViewMode = false
}) => {
  const [proteinName, setProteinName] = useState('');
  const [proteinSequence, setProteinSequence] = useState('');
  const [batchName, setBatchName] = useState(generateRandomJobName());
  const [ligands, setLigands] = useState<LigandData[]>([{ name: '', smiles: '' }]);
  const [isRunning, setIsRunning] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  // Boltz-2 parameters
  const [recyclingSteps, setRecyclingSteps] = useState(3);
  const [samplingSteps, setSamplingSteps] = useState(200);
  const [diffusionSamples, setDiffusionSamples] = useState(1);
  const [maxConcurrent, setMaxConcurrent] = useState(2);
  
  // Status tracking
  const [currentBatchId, setCurrentBatchId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  
  const addLigand = useCallback(() => {
    setLigands(prev => [...prev, { name: '', smiles: '' }]);
  }, []);
  
  const removeLigand = useCallback((index: number) => {
    setLigands(prev => prev.filter((_, i) => i !== index));
  }, []);
  
  const updateLigand = useCallback((index: number, field: keyof LigandData, value: string) => {
    setLigands(prev => prev.map((ligand, i) => 
      i === index ? { ...ligand, [field]: value } : ligand
    ));
  }, []);
  
  // Validation
  const isValid = () => {
    if (!proteinSequence.trim()) return false;
    if (ligands.length === 0) return false;
    if (ligands.some(l => !l.name.trim() || !l.smiles.trim())) return false;
    return true;
  };
  
  const handleSubmit = async () => {
    if (!isValid() || isRunning) return;
    
    try {
      setIsRunning(true);
      setProgress(0);
      onPredictionStart();
      
      console.log('🚀 Submitting batch prediction...');
      console.log('   Protein:', proteinName || 'Unnamed');
      console.log('   Ligands:', ligands.length);
      console.log('   Batch name:', batchName);
      
      // Submit batch prediction using new API
      const batch = await jobStore.submitBatchPrediction({
        protein_sequence: proteinSequence,
        ligands: ligands.map(ligand => ({
          name: ligand.name,
          smiles: ligand.smiles
        })),
        batch_name: batchName,
        max_concurrent: maxConcurrent,
        recycling_steps: recyclingSteps,
        sampling_steps: samplingSteps,
        diffusion_samples: diffusionSamples
      });
      
      setCurrentBatchId(batch.id);
      
      console.log(`✅ Batch submitted: ${batch.id}`);
      
      // Subscribe to batch updates
      const unsubscribe = jobStore.subscribeToBatch(batch.id, (updatedBatch) => {
        console.log(`📊 Batch update: ${updatedBatch.id} - ${updatedBatch.status} (${updatedBatch.progress}%)`);
        
        setProgress(updatedBatch.progress);
        
        if (updatedBatch.status === 'completed') {
          setIsRunning(false);
          
          // Convert to format expected by parent component
          const result = {
            batch_id: updatedBatch.id,
            status: 'completed',
            total_jobs: updatedBatch.total_jobs,
            completed_jobs: updatedBatch.completed_jobs,
            results: updatedBatch.results,
            batch_name: updatedBatch.batch_name,
            created_at: updatedBatch.created_at,
            completed_at: updatedBatch.completed_at
          };
          
          onPredictionComplete(result);
          unsubscribe();
        } else if (updatedBatch.status === 'failed') {
          setIsRunning(false);
          onPredictionError(`Batch prediction failed: ${updatedBatch.id}`);
          unsubscribe();
        }
      });
      
    } catch (error) {
      console.error('🚨 Batch submission failed:', error);
      setIsRunning(false);
      onPredictionError(error instanceof Error ? error.message : 'Batch submission failed');
    }
  };
  
  // Load example data
  const loadExample = () => {
    setProteinName('Acetylcholinesterase');
    setProteinSequence('MKFLKFSLLTLLLFSSAYSRGVFRRDAHKSEVAHRFKDLGEENFKALVLIAFAQYLQQCPFEDHVKLVNEVTEFAKTCVADESAENCDKSLHTLFGDKLCTVATLRETYGEMADCCAKQEPERNECFLQHKDDNPNLPRLVRPEVDVMCTAFHDNEETFLKKYLYEIARRHPYFYAPELLFFAKRYKAAFTECCQAADKAACLLPKLDELRDEGKASSAKQRLKCASLQKFGERAFKAWAVARLSQRFPKAEFAEVSKLVTDLTKVHTECCHGDLLECADDRADLAKYICENQDSISSKLKECCEKPLLEKSHCIAEVENDEMPADLPSLAADFVESKDVCKNYAEAKDVFLGMFLYEYARRHPDYSVVLLLRLAKTYETTLEKCCAAADPHECYAKVFDEFKPLVEEPQNLIKQNCELFEQLGEYKFQNALLVRYTKKVPQVSTPTLVEVSRNLGKVGSKCCKHPEAKRMPCAEDYLSVVLNQLCVLHEKTPVSDRVTKCCTESLVNRRPCFSALEVDETYVPKEFNAETFTFHADICTLSEKERQIKKQTALVELVKHKPKATKEQLKAVMDDFAAFVEKCCKADDKETCFAEEGKKLVAASQAALGL');
    setLigands([
      { name: 'Donepezil', smiles: 'COc1cc(CC(CCN2CCN(Cc3ccccc3)CC2)C(=O)c2ccccc2)ccc1O' },
      { name: 'Rivastigmine', smiles: 'CCN(C)C(=O)Oc1cccc(C(C)N(C)C)c1' },
      { name: 'Galantamine', smiles: 'COc1ccc2c3c1O[C@@H]1C[C@@H](O)C=C[C@@H]1N(C)[C@@H]3Cc1ccccc1-2' }
    ]);
    setBatchName('AChE_inhibitors_batch');
  };
  
  if (isViewMode) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-lg">Batch Protein-Ligand Input (Read Only)</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600">
            This component is in view mode. Data will be loaded from the results.
          </p>
        </CardContent>
      </Card>
    );
  }
  
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            Batch Protein-Ligand Prediction
          </CardTitle>
          <p className="text-sm text-gray-600">
            Submit multiple ligands against a single protein using Boltz-2 for parallel processing.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          
          {/* Batch Configuration */}
          <div className="space-y-2">
            <Label htmlFor="batchName">Batch Name</Label>
            <Input
              id="batchName"
              value={batchName}
              onChange={(e) => setBatchName(e.target.value)}
              placeholder="Enter batch name"
              disabled={isRunning}
            />
          </div>
          
          {/* Protein Input */}
          <div className="space-y-2">
            <Label htmlFor="proteinName">Protein Name (Optional)</Label>
            <Input
              id="proteinName"
              value={proteinName}
              onChange={(e) => setProteinName(e.target.value)}
              placeholder="e.g., Acetylcholinesterase"
              disabled={isRunning}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="proteinSequence">Protein Sequence *</Label>
            <Textarea
              id="proteinSequence"
              value={proteinSequence}
              onChange={(e) => setProteinSequence(e.target.value)}
              placeholder="Enter protein sequence in FASTA format..."
              rows={4}
              disabled={isRunning}
              className="font-mono text-sm"
            />
          </div>
          
          {/* Ligands Section */}
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <Label>Ligands ({ligands.length})</Label>
              <Button 
                onClick={addLigand} 
                size="sm" 
                variant="outline"
                disabled={isRunning}
              >
                Add Ligand
              </Button>
            </div>
            
            {ligands.map((ligand, index) => (
              <div key={index} className="grid grid-cols-1 md:grid-cols-3 gap-2 p-3 border rounded-lg">
                <Input
                  value={ligand.name}
                  onChange={(e) => updateLigand(index, 'name', e.target.value)}
                  placeholder={`Ligand ${index + 1} name`}
                  disabled={isRunning}
                />
                <Input
                  value={ligand.smiles}
                  onChange={(e) => updateLigand(index, 'smiles', e.target.value)}
                  placeholder="SMILES string"
                  className="font-mono text-sm"
                  disabled={isRunning}
                />
                <Button
                  onClick={() => removeLigand(index)}
                  size="sm"
                  variant="destructive"
                  disabled={isRunning || ligands.length === 1}
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
          
          {/* Advanced Parameters */}
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Switch
                id="advanced"
                checked={showAdvanced}
                onCheckedChange={setShowAdvanced}
                disabled={isRunning}
              />
              <Label htmlFor="advanced">Advanced Parameters</Label>
            </div>
            
            {showAdvanced && (
              <div className="grid grid-cols-2 gap-4 p-4 border rounded-lg bg-gray-50">
                <div className="space-y-2">
                  <Label htmlFor="recycling">Recycling Steps</Label>
                  <Input
                    id="recycling"
                    type="number"
                    value={recyclingSteps}
                    onChange={(e) => setRecyclingSteps(Number(e.target.value))}
                    min={1}
                    max={10}
                    disabled={isRunning}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="sampling">Sampling Steps</Label>
                  <Input
                    id="sampling"
                    type="number"
                    value={samplingSteps}
                    onChange={(e) => setSamplingSteps(Number(e.target.value))}
                    min={50}
                    max={500}
                    disabled={isRunning}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="diffusion">Diffusion Samples</Label>
                  <Input
                    id="diffusion"
                    type="number"
                    value={diffusionSamples}
                    onChange={(e) => setDiffusionSamples(Number(e.target.value))}
                    min={1}
                    max={5}
                    disabled={isRunning}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="concurrent">Max Concurrent Jobs</Label>
                  <Input
                    id="concurrent"
                    type="number"
                    value={maxConcurrent}
                    onChange={(e) => setMaxConcurrent(Number(e.target.value))}
                    min={1}
                    max={5}
                    disabled={isRunning}
                  />
                  <p className="text-xs text-gray-500">
                    Cloud Run optimized for concurrency=2
                  </p>
                </div>
              </div>
            )}
          </div>
          
          {/* Progress Display */}
          {isRunning && (
            <Alert>
              <Loader2 className="h-4 w-4 animate-spin" />
              <AlertDescription>
                Batch processing in progress... {progress}% complete
                {currentBatchId && (
                  <div className="text-xs mt-1 font-mono">
                    Batch ID: {currentBatchId}
                  </div>
                )}
              </AlertDescription>
            </Alert>
          )}
          
          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button
              onClick={handleSubmit}
              disabled={!isValid() || isRunning}
              className="flex items-center gap-2"
            >
              {isRunning ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              {isRunning ? 'Processing...' : 'Start Batch Prediction'}
            </Button>
            
            <Button
              onClick={loadExample}
              variant="outline"
              disabled={isRunning}
              className="flex items-center gap-2"
            >
              <FileText className="w-4 h-4" />
              Load Example
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default BatchProteinLigandInputSimplified;