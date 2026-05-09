// Workspace layering system - machine ID constants for consistency
const MACHINES = [
  { id: 'ubuntu', label: 'ubuntu home', hostname: '127.0.0.1', default_workspace: '~', color: 'blue' },
  { id: 'popos', label: 'pop! os home', hostname: '127.0.0.1', default_workspace: '~', color: 'yellow' }
];

function getMachines() { return MACHINES; }

console.log('workspace layering loaded');
