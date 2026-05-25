import { useEffect, useRef, useState } from 'react';

interface PcbViewerProps {
  glbUrl: string;
  onClose: () => void;
}

export default function PcbViewer({ glbUrl, onClose }: PcbViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!glbUrl || !containerRef.current) return;

    let cleanup: () => void = () => {};

    import('three').then((THREE) => {
      import('three/addons/loaders/GLTFLoader.js').then(({ GLTFLoader }) => {
        import('three/addons/controls/OrbitControls.js').then(({ OrbitControls }) => {
          const container = containerRef.current;
          if (!container) return;

          const scene = new THREE.Scene();
          scene.background = new THREE.Color(0x1a1a2e);

          const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 1000);
          camera.position.set(100, 80, 100);

          const renderer = new THREE.WebGLRenderer({ antialias: true });
          renderer.setSize(container.clientWidth, container.clientHeight);
          renderer.setPixelRatio(window.devicePixelRatio);
          renderer.shadowMap.enabled = true;
          container.appendChild(renderer.domElement);

          const controls = new OrbitControls(camera, renderer.domElement);
          controls.enableDamping = true;
          controls.dampingFactor = 0.1;
          controls.target.set(0, 0, 0);

          const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
          scene.add(ambientLight);

          const dirLight = new THREE.DirectionalLight(0xffffff, 1);
          dirLight.position.set(50, 100, 50);
          scene.add(dirLight);

          const gridHelper = new THREE.GridHelper(200, 20, 0x444488, 0x333366);
          scene.add(gridHelper);

          const loader = new GLTFLoader();
          loader.load(
            glbUrl,
            (gltf) => {
              scene.add(gltf.scene);
              const box = new THREE.Box3().setFromObject(gltf.scene);
              const center = box.getCenter(new THREE.Vector3());
              const size = box.getSize(new THREE.Vector3());
              const maxDim = Math.max(size.x, size.y, size.z);
              const dist = maxDim * 1.5;
              camera.position.set(dist, dist * 0.8, dist);
              controls.target.copy(center);
              controls.update();
              setLoading(false);
            },
            undefined,
            (err) => {
              setError(`Failed to load 3D model: ${err instanceof Error ? err.message : 'Unknown error'}`);
              setLoading(false);
            }
          );

          const animate = () => {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
          };
          animate();

          const handleResize = () => {
            const w = container.clientWidth;
            const h = container.clientHeight;
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            renderer.setSize(w, h);
          };
          window.addEventListener('resize', handleResize);

          cleanup = () => {
            window.removeEventListener('resize', handleResize);
            controls.dispose();
            renderer.dispose();
            if (container.contains(renderer.domElement)) {
              container.removeChild(renderer.domElement);
            }
          };
        });
      });
    });

    return cleanup;
  }, [glbUrl]);

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center" onClick={onClose}>
      <div className="relative w-[90vw] h-[85vh] bg-gray-900 rounded-xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center text-white text-lg">
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              Loading 3D model...
            </div>
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center text-red-400 text-lg">
            {error}
          </div>
        )}
        <div ref={containerRef} className="w-full h-full" style={{ display: error ? 'none' : 'block' }} />
        <button
          onClick={onClose}
          className="absolute top-3 right-3 bg-gray-800 hover:bg-gray-700 text-white rounded-full w-8 h-8 flex items-center justify-center z-10"
        >
          ✕
        </button>
        <div className="absolute bottom-3 left-3 text-gray-400 text-xs bg-gray-900/80 px-2 py-1 rounded">
          Drag to rotate · Scroll to zoom · Right-drag to pan
        </div>
      </div>
    </div>
  );
}
