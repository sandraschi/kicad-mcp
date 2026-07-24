import { useEffect, useRef, useState } from 'react';
import { apiPost } from '../lib/api';

export default function PcbViewer3D({ boardName, onBoardChange }: { boardName: string; onBoardChange: (name: string) => void }) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [boards, setBoards] = useState<string[]>([]);
  const [glbUrl, setGlbUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiPost('/api/v1/board/preview', {}).then((d) => {
      if (d.boards) setBoards(d.boards.map((b: any) => b.name));
    }).catch(() => {});
  }, []);

  const loadBoard = async (name: string) => {
    setLoading(true);
    onBoardChange(name);
    try {
      const r = await apiPost('/api/v1/board/preview', { file_name: name });
      if (r.success && r.glb_url) setGlbUrl(r.glb_url);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    if (!mountRef.current || !glbUrl) return;
    const el = mountRef.current;
    let controls: any, renderer: any, resizeObserver: any, animId = 0;

    async function init() {
      const THREE = await import('three');
      const OCMod: any = await import('three/examples/jsm/controls/OrbitControls');
      const OC = OCMod.OrbitControls;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0a0a0f);

      const camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 0.1, 1000);
      camera.position.set(80, 60, 80);

      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(el.clientWidth, el.clientHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      renderer.shadowMap.enabled = true;
      el.appendChild(renderer.domElement);

      controls = new OC(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.minDistance = 10;
      controls.maxDistance = 500;

      // Lights
      scene.add(new THREE.AmbientLight(0x404060, 0.6));
      const dir = new THREE.DirectionalLight(0xffffff, 1.5);
      dir.position.set(50, 80, 50);
      scene.add(dir);
      const dir2 = new THREE.DirectionalLight(0x8888ff, 0.4);
      dir2.position.set(-50, 30, -50);
      scene.add(dir2);

      // Ground grid
      scene.add(new THREE.GridHelper(100, 30, 0x333355, 0x222244));

      // Load GLB
      try {
        const GLTFMod: any = await import('three/examples/jsm/loaders/GLTFLoader');
        const loader = new GLTFMod.GLTFLoader();
        const gltf = await new Promise<any>((resolve, reject) => {
          loader.load(glbUrl, resolve, undefined, reject);
        });
        gltf.scene.traverse((node: any) => {
          if (node.isMesh) {
            node.castShadow = true;
            node.receiveShadow = true;
          }
        });
        const box = new THREE.Box3().setFromObject(gltf.scene);
        const center = box.getCenter(new THREE.Vector3());
        gltf.scene.position.sub(center as any);
        const size = box.getSize(new THREE.Vector3()).length();
        if (size > 0) {
          camera.position.set(size * 2, size * 1.5, size * 2);
          controls.target.set(0, 0, 0);
        }
        scene.add(gltf.scene);
      } catch {
        // Fallback: procedural board
        const mat = new THREE.MeshStandardMaterial({ color: 0x0d5e2e, metalness: 0.1, roughness: 0.8 });
        const board = new THREE.Mesh(new THREE.BoxGeometry(40, 1.6, 30), mat);
        board.position.y = -0.8;
        scene.add(board);
        const traceMat = new THREE.MeshStandardMaterial({ color: 0xcd7f32, metalness: 0.7, roughness: 0.3 });
        for (let i = 0; i < 20; i++) {
          const t = new THREE.Mesh(new THREE.BoxGeometry(3 + Math.random() * 8, 0.1, 0.2 + Math.random() * 0.3), traceMat);
          t.position.set(-15 + Math.random() * 30, 0, -12 + Math.random() * 24);
          t.rotation.y = Math.random() * Math.PI;
          scene.add(t);
        }
      }

      function animate() {
        animId = requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
      }
      animate();

      resizeObserver = new ResizeObserver(() => {
        camera.aspect = el.clientWidth / el.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(el.clientWidth, el.clientHeight);
      });
      resizeObserver.observe(el);
    }

    init();

    return () => {
      cancelAnimationFrame(animId);
      if (resizeObserver) resizeObserver.disconnect();
      if (controls) controls.dispose();
      if (renderer) {
        renderer.dispose();
        if (renderer.domElement?.parentElement === el) el.removeChild(renderer.domElement);
      }
    };
  }, [glbUrl]);

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <select
          value={boardName}
          onChange={(e) => loadBoard(e.target.value)}
          className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1 text-xs flex-1"
        >
          <option value="">Select a board to preview...</option>
          {boards.map((b) => <option key={b} value={b}>{b}</option>)}
        </select>
        {loading && <span className="text-xs text-gray-500">Loading GLB...</span>}
      </div>
      <div ref={mountRef} className="w-full h-72 rounded-lg overflow-hidden bg-zinc-950" />
    </div>
  );
}
