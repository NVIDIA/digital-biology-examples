from urllib3.util import Retry
from requests import Session
from requests.adapters import HTTPAdapter
import numpy as np

class GenMol_Generator:
    __default_params__ = {
        "num_molecules": 10,
        "temperature": 1.0,
        "noise": 0.0,
        'step_size': 1,
        'unique': True,
        'scoring': 'QED'
    }
    
    def __init__(self, invoke_url = 'http://127.0.0.1:8000/generate', auth = None, **kwargs):
        self.invoke_url = invoke_url
        self.auth = auth
        self.session = Session()
        self.num_generate = kwargs.get('num_generate', 1)
        self.verbose = False
        self.max_retries = kwargs.get('max_retries', 5)
        self.retries = Retry(
            total = self.max_retries,
            backoff_factor = 0.1,
            status_forcelist = [400],
            allowed_methods = {'POST'},
        )
        self.session.mount(self.invoke_url, HTTPAdapter(max_retries = self.retries))
    
    def _validate_input(self, molecules, num_generate):
        """Validate input parameters before processing."""
        # Check if molecules is provided and not empty
        if molecules is None:
            raise ValueError("molecules parameter cannot be None")
        
        if not isinstance(molecules, (list, tuple)):
            raise TypeError("molecules must be a list or tuple")
        
        if len(molecules) == 0:
            raise ValueError("molecules list cannot be empty")
        
        # Validate each molecule SMILES string
        for i, m in enumerate(molecules):
            if not isinstance(m, str):
                raise TypeError(f"molecule at index {i} must be a string, got {type(m).__name__}")
            
            if len(m.strip()) == 0:
                raise ValueError(f"molecule at index {i} is empty or whitespace only")
        
        # Validate num_generate
        if not isinstance(num_generate, int):
            raise TypeError("num_generate must be an integer")
        
        if num_generate <= 0:
            raise ValueError("num_generate must be a positive integer")
        
        return True
    
    def produce(self, molecules, num_generate):
        # Validate inputs
        self._validate_input(molecules, num_generate)
        
        generated = []
        
        for m in molecules:
            safe_segs = m.split('.')
            
            # Validate that splitting produced valid segments
            if len(safe_segs) == 0 or all(len(seg.strip()) == 0 for seg in safe_segs):
                continue
            
            pos = np.random.randint(len(safe_segs))
            safe_segs[pos] = '[*{%d-%d}]' % (len(safe_segs[pos]), len(safe_segs[pos]) + 5)
            smiles = '.'.join(safe_segs)
    
            new_molecules = self.inference(
                smiles = smiles,
                num_molecules = max(10, num_generate),
                temperature = 1.5,
                noise = 2.0
            )
            new_molecules = [_['smiles'] for _ in new_molecules]
            
            if len(new_molecules) == 0:
                return []
                
            new_molecules = new_molecules[:(min(self.num_generate, len(new_molecules)))]
            generated.extend(new_molecules)
        
        self.molecules = list(set(generated))
        return self.molecules
    
    def inference(self, **params):
        headers = {
            "Authorization": "" if self.auth is None else "Bearer " + self.auth,
            "Content-Type": "application/json"
        }
        task = GenMol_Generator.__default_params__.copy()
        task.update(params)
        if self.verbose:
            print("TASK:", str(task))
        
        json_data = {k : str(v) for k, v in task.items()}
        
        response = self.session.post(self.invoke_url, headers=headers, json=json_data)
        response.raise_for_status()
        output = response.json()
        assert output['status'] == 'success'
        return output['molecules']
