import { useEffect, useRef } from 'react';

export default function PcbViewer3D({ toolCount, boardAvailable }: { toolCount: number; boardAvailable: boolean }) {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!mountRef.current) return;
    const el = mountRef.current;
    let controls: any;
    let renderer: any;
    let resizeObserver: any;
    let animId = 0;

    async function init() {
      const THREE = await import('three');
      const OCMod: any = await import('three/examples/jsm/controls/OrbitControls');
      const OC = OCMod.OrbitControls;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0a0a0f);

      const camera = new THREE.PerspectiveCamera(45, el.clientWidth / el.clientHeight, 0.1, 1000);
      camera.position.set(60, 40, 60);

      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(el.clientWidth, el.clientHeight);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
      el.appendChild(renderer.domElement);

      controls = new OC(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.minDistance = 10;
      controls.maxDistance = 200;

      const ambient = new THREE.AmbientLight(0x404060, 0.5);
      scene.add(ambient);
      const dir = new THREE.DirectionalLight(0xffffff, 1.2);
      dir.position.set(30, 50, 30);
      scene.add(dir);
      const dir2 = new THREE.DirectionalLight(0x8888ff, 0.4);
      dir2.position.set(-30, 20, -30);
      scene.add(dir2);

      const boardGeo = new THREE.BoxGeometry(40, 1.6, 30);
      const boardMat = new THREE.MeshStandardMaterial({ color: 0x0d5e2e, metalness: 0.1, roughness: 0.8 });
      const board = new THREE.Mesh(boardGeo, boardMat);
      board.position.y = -0.8;
      scene.add(board);

      const traceMat = new THREE.MeshStandardMaterial({ color: 0xcd7f32, metalness: 0.7, roughness: 0.3 });
      for (let i = 0; i < Math.min(toolCount, 30); i++) {
        const w = 0.2 + Math.random() * 0.3;
        const len = 3 + Math.random() * 8;
        const trace = new THREE.Mesh(new THREE.BoxGeometry(len, 0.1, w), traceMat);
        trace.position.set(-15 + Math.random() * 30, 0, -12 + Math.random() * 24);
        trace.rotation.y = Math.random() * Math.PI;
        scene.add(trace);
      }

      const icMat = new THREE.MeshStandardMaterial({ color: 0x222222, metalness: 0.3, roughness: 0.6 });
      const capMat = new THREE.MeshStandardMaterial({ color: 0x1a5276, metalness: 0.1, roughness: 0.5 });
      for (let i = 0; i < 8; i++) {
        const ic = new THREE.Mesh(new THREE.BoxGeometry(3 + Math.random() * 2, 0.4, 3 + Math.random() * 2), icMat);
        ic.position.set(-14 + Math.random() * 28, 0.2, -10 + Math.random() * 20);
        scene.add(ic);
      }
      for (let i = 0; i < 12; i++) {
        const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 0.8, 1.2, 12), capMat);
        cap.position.set(-16 + Math.random() * 32, 0.6, -11 + Math.random() * 22);
        scene.add(cap);
      }

      const grid = new THREE.GridHelper(60, 20, 0x333355, 0x222244);
      grid.position.y = 0;
      scene.add(grid);

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
  }, [toolCount, boardAvailable]);

  return <div ref={mountRef} className="w-full h-64 rounded-lg overflow-hidden" />;
}
