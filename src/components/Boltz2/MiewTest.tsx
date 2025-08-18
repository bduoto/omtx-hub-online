import React from 'react';
// import Viewer from 'miew-react'; // Commented out - module doesn't exist

const MiewTest: React.FC = () => {
  const testCifContent = `
data_test
_cell.length_a    10.0
_cell.length_b    10.0
_cell.length_c    10.0
_cell.angle_alpha 90.0
_cell.angle_beta  90.0
_cell.angle_gamma 90.0
_symmetry.space_group_name_H-M 'P 1'
loop_
_atom_site.label_atom_id
_atom_site.type_symbol
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
C1 C 0.0 0.0 0.0
C2 C 0.1 0.1 0.1
`;

  const miewOptions = {
    load: testCifContent,
    settings: {
      bg: { color: 0x1a1a1a },
      axes: false,
      fps: false,
      fog: true,
      ao: true,
      fxaa: true
    }
  };

  const handleInit = (miew: any) => {
    console.log('Miew initialized:', miew);
  };

  return (
    <div className="p-4">
      <h3 className="text-white text-lg font-semibold mb-4">Miew Test Component</h3>
      <div className="bg-gray-800 rounded-lg p-4" style={{ height: '300px' }}>
        {/* <Viewer
          options={miewOptions}
          onInit={handleInit}
        /> */}
        <div className="text-center text-gray-400 mt-16">
          Miew viewer not available - module doesn't exist
        </div>
      </div>
    </div>
  );
};

export default MiewTest; 