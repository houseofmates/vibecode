// Workspace layering system - machine ID constants for consistency
const MACHINES = [
  { id: 'ubuntu', label: 'ubuntu home', hostname: '192.168.4.250', default_workspace: '/home/house', color: 'blue' },
  { id: 'popos', label: 'pop! os home', hostname: '192.168.4.233', default_workspace: '/home/house', color: 'yellow' }
];

function getMachines() { return MACHINES; }

console.log('workspace layering loaded');
