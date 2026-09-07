import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';

export const PolyHero3D: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [activeStep, setActiveStep] = useState<string>('LISTEN');
  const [webGLError, setWebGLError] = useState<boolean>(false);

  useEffect(() => {
    if (!containerRef.current || !canvasRef.current) return;

    // Check prefers-reduced-motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Scene Setup
    const scene = new THREE.Scene();
    
    // Responsive Camera Setup (with zero-size fallback protection)
    const width = Math.max(containerRef.current.clientWidth || 1, 1);
    const height = Math.max(containerRef.current.clientHeight || 1, 1);
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 0, 8.5);

    // WebGL Renderer Setup with WebGL1/WebGL2 safety wrapper
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas: canvasRef.current,
        alpha: true,
        antialias: true,
        powerPreference: 'high-performance'
      });
      renderer.setSize(width, height, false);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    } catch (e) {
      console.warn('WebGL initialization failed, using CSS fallback visual:', e);
      setWebGLError(true);
      return;
    }

    // Lights Setup (POLY Brand Colors)
    const ambientLight = new THREE.AmbientLight(0xFFF8F5, 1.2);
    scene.add(ambientLight);

    // Primary Light (Soft Light Blue #38607A)
    const mainLight = new THREE.DirectionalLight(0x38607A, 2.5);
    mainLight.position.set(5, 5, 7);
    scene.add(mainLight);

    // Rim/Accent Light (Muted Lavender #69577E)
    const rimLight = new THREE.DirectionalLight(0x69577E, 2.0);
    rimLight.position.set(-5, -3, -4);
    scene.add(rimLight);

    // Warm Fill Light (Muted Dusty Rose #7E4F50)
    const warmLight = new THREE.PointLight(0x7E4F50, 1.5, 15);
    warmLight.position.set(0, -3, 3);
    scene.add(warmLight);

    // Central POLY Intelligence Core Group
    const polyCoreGroup = new THREE.Group();
    scene.add(polyCoreGroup);

    // 1. Central Translucent Sphere (POLY Core)
    const sphereGeo = new THREE.IcosahedronGeometry(1.8, 3);
    const sphereMat = new THREE.MeshStandardMaterial({
      color: 0x38607A,
      emissive: 0x263845,
      roughness: 0.25,
      metalness: 0.1,
      transparent: true,
      opacity: 0.85
    });
    const mainSphere = new THREE.Mesh(sphereGeo, sphereMat);
    polyCoreGroup.add(mainSphere);

    // Inner Glowing Core
    const innerGeo = new THREE.IcosahedronGeometry(1.1, 2);
    const innerMat = new THREE.MeshStandardMaterial({
      color: 0x69577E,
      emissive: 0x69577E,
      emissiveIntensity: 0.4,
      roughness: 0.3,
      metalness: 0.2,
      wireframe: true
    });
    const innerCore = new THREE.Mesh(innerGeo, innerMat);
    polyCoreGroup.add(innerCore);

    // 2. 3D Animated Waveform Rings
    const waveRingGroup = new THREE.Group();
    polyCoreGroup.add(waveRingGroup);

    const ringGeo1 = new THREE.TorusGeometry(2.4, 0.03, 16, 100);
    const ringMat1 = new THREE.MeshStandardMaterial({
      color: 0x38607A,
      emissive: 0x38607A,
      emissiveIntensity: 0.5,
      roughness: 0.2
    });
    const waveRing1 = new THREE.Mesh(ringGeo1, ringMat1);
    waveRing1.rotation.x = Math.PI / 3;
    waveRingGroup.add(waveRing1);

    const ringGeo2 = new THREE.TorusGeometry(2.8, 0.025, 16, 100);
    const ringMat2 = new THREE.MeshStandardMaterial({
      color: 0x69577E,
      emissive: 0x69577E,
      emissiveIntensity: 0.6,
      roughness: 0.2
    });
    const waveRing2 = new THREE.Mesh(ringGeo2, ringMat2);
    waveRing2.rotation.y = Math.PI / 4;
    waveRingGroup.add(waveRing2);

    const ringGeo3 = new THREE.TorusGeometry(3.2, 0.02, 16, 100);
    const ringMat3 = new THREE.MeshStandardMaterial({
      color: 0x7E4F50,
      emissive: 0x7E4F50,
      emissiveIntensity: 0.5,
      roughness: 0.2
    });
    const waveRing3 = new THREE.Mesh(ringGeo3, ringMat3);
    waveRing3.rotation.x = -Math.PI / 4;
    waveRingGroup.add(waveRing3);

    // 3. Floating 3D Node Texture Generator
    const createNodeSprite = (text: string, bgColor: string, textColor: string, badgeIcon?: string) => {
      const canvas = document.createElement('canvas');
      canvas.width = 300;
      canvas.height = 80;
      const ctx = canvas.getContext('2d');
      if (!ctx) return null;

      // Draw Rounded Capsule Box
      ctx.fillStyle = bgColor;
      ctx.shadowColor = 'rgba(38, 56, 69, 0.15)';
      ctx.shadowBlur = 12;
      ctx.shadowOffsetY = 4;

      const r = 24;
      const w = canvas.width - 10;
      const h = canvas.height - 10;
      const x = 5;
      const y = 5;

      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.lineTo(x + w - r, y);
      ctx.quadraticCurveTo(x + w, y, x + w, y + r);
      ctx.lineTo(x + w, y + h - r);
      ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      ctx.lineTo(x + r, y + h);
      ctx.quadraticCurveTo(x, y + h, x, y + h - r);
      ctx.lineTo(x, y + r);
      ctx.quadraticCurveTo(x, y, x + r, y);
      ctx.closePath();
      ctx.fill();

      // Border
      ctx.lineWidth = 2;
      ctx.strokeStyle = '#BFC9D0';
      ctx.stroke();

      // Text
      ctx.fillStyle = textColor;
      ctx.font = 'bold 24px "Plus Jakarta Sans", sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText((badgeIcon ? badgeIcon + ' ' : '') + text, canvas.width / 2, canvas.height / 2);

      const texture = new THREE.CanvasTexture(canvas);
      texture.generateMipmaps = false;
      texture.minFilter = THREE.LinearFilter;
      const spriteMat = new THREE.SpriteMaterial({ map: texture, transparent: true, opacity: 0.95 });
      const sprite = new THREE.Sprite(spriteMat);
      sprite.scale.set(1.8, 0.48, 1);
      return sprite;
    };

    // Create Orbiting Nodes
    const nodesGroup = new THREE.Group();
    polyCoreGroup.add(nodesGroup);

    const node1 = createNodeSprite('Hindi • Hinglish', '#FFF8F5', '#69577E', '🌐');
    if (node1) { node1.position.set(-2.8, 1.6, 0.8); nodesGroup.add(node1); }

    const node2 = createNodeSprite('Listening...', '#FFF8F5', '#38607A', '🎙️');
    if (node2) { node2.position.set(2.7, 1.4, 0.5); nodesGroup.add(node2); }

    const node3 = createNodeSprite('Confirmed ✓', '#FFF8F5', '#38607A', '✓');
    if (node3) { node3.position.set(-2.9, -1.5, 0.6); nodesGroup.add(node3); }

    const node4 = createNodeSprite('Confidence: High', '#FFF8F5', '#69577E', '⚡');
    if (node4) { node4.position.set(2.8, -1.3, 0.7); nodesGroup.add(node4); }

    const node5 = createNodeSprite('Human Ready', '#FFF8F5', '#7E4F50', '🤝');
    if (node5) { node5.position.set(0, -2.5, 1.2); nodesGroup.add(node5); }

    // Floating Particles (Soft Ambient Dust)
    const particleGeo = new THREE.BufferGeometry();
    const particleCount = 40;
    const posArray = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      posArray[i] = (Math.random() - 0.5) * 12;
      posArray[i + 1] = (Math.random() - 0.5) * 12;
      posArray[i + 2] = (Math.random() - 0.5) * 8;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
    const particleMat = new THREE.PointsMaterial({
      size: 0.05,
      color: 0x38607A,
      transparent: true,
      opacity: 0.4
    });
    const particlesMesh = new THREE.Points(particleGeo, particleMat);
    scene.add(particlesMesh);

    // Mouse Parallax Damping Variables
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;

    const handleMouseMove = (event: MouseEvent) => {
      const windowHalfX = window.innerWidth / 2;
      const windowHalfY = window.innerHeight / 2;
      mouseX = (event.clientX - windowHalfX) / windowHalfX;
      mouseY = (event.clientY - windowHalfY) / windowHalfY;
    };

    window.addEventListener('mousemove', handleMouseMove);

    // Scroll Reaction Listener
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const heroHeight = containerRef.current?.clientHeight || 600;
      const scrollProgress = Math.min(scrollY / heroHeight, 1);

      // Determine active storytelling step
      if (scrollProgress < 0.25) setActiveStep('LISTEN');
      else if (scrollProgress < 0.5) setActiveStep('UNDERSTAND');
      else if (scrollProgress < 0.75) setActiveStep('CONFIRM');
      else setActiveStep('ESCALATE');

      // Modulate 3D camera & scene based on scroll
      camera.position.z = 8.5 + scrollProgress * 1.5;
      polyCoreGroup.rotation.z = scrollProgress * 0.3;
    };

    window.addEventListener('scroll', handleScroll, { passive: true });

    // Window Resize Listener
    const handleResize = () => {
      if (!containerRef.current || !canvasRef.current || !renderer) return;
      const newW = containerRef.current.clientWidth;
      const newH = containerRef.current.clientHeight;
      if (newW > 0 && newH > 0) {
        camera.aspect = newW / newH;
        camera.updateProjectionMatrix();
        renderer.setSize(newW, newH, false);
      }
    };

    window.addEventListener('resize', handleResize);

    // Animation Loop with framerate-independent performance.now()
    const startTime = performance.now();
    let animationFrameId: number;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      if (!containerRef.current || containerRef.current.clientWidth === 0 || containerRef.current.clientHeight === 0) {
        return;
      }

      const elapsedTime = (performance.now() - startTime) / 1000;

      if (!prefersReducedMotion) {
        // Continuous Ambient Motion
        polyCoreGroup.rotation.y = elapsedTime * 0.15;
        innerCore.rotation.y = -elapsedTime * 0.25;
        innerCore.rotation.x = elapsedTime * 0.15;

        waveRing1.rotation.z = elapsedTime * 0.2;
        waveRing2.rotation.z = -elapsedTime * 0.25;
        waveRing3.rotation.z = elapsedTime * 0.15;

        // Gentle Floating Bob
        polyCoreGroup.position.y = Math.sin(elapsedTime * 1.2) * 0.15;
        mainSphere.scale.setScalar(1 + Math.sin(elapsedTime * 2) * 0.03);

        // Node Orbital Movement
        const orbitRadius = 0.08;
        if (node1) node1.position.y = 1.6 + Math.sin(elapsedTime * 1.5) * orbitRadius;
        if (node2) node2.position.y = 1.4 + Math.cos(elapsedTime * 1.7) * orbitRadius;
        if (node3) node3.position.y = -1.5 + Math.sin(elapsedTime * 1.4 + 1) * orbitRadius;
        if (node4) node4.position.y = -1.3 + Math.cos(elapsedTime * 1.6 + 2) * orbitRadius;
        if (node5) node5.position.y = -2.5 + Math.sin(elapsedTime * 1.8 + 3) * orbitRadius;

        // Mouse Parallax Damping (Lerp)
        targetX = mouseX * 0.4;
        targetY = mouseY * 0.3;
        polyCoreGroup.rotation.y += (targetX - polyCoreGroup.rotation.y) * 0.05;
        polyCoreGroup.rotation.x += (targetY - polyCoreGroup.rotation.x) * 0.05;

        particlesMesh.rotation.y = elapsedTime * 0.03;
      }

      if (renderer) {
        renderer.render(scene, camera);
      }
    };

    animate();

    // Clean Cleanup
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);

      sphereGeo.dispose();
      sphereMat.dispose();
      innerGeo.dispose();
      innerMat.dispose();
      ringGeo1.dispose();
      ringMat1.dispose();
      ringGeo2.dispose();
      ringMat2.dispose();
      ringGeo3.dispose();
      ringMat3.dispose();
      particleGeo.dispose();
      particleMat.dispose();
      if (renderer) {
        renderer.dispose();
      }
    };
  }, []);

  return (
    <div ref={containerRef} className="relative w-full h-[520px] md:h-[620px] flex items-center justify-center overflow-hidden">
      
      {/* Three.js Canvas or Fallback */}
      {!webGLError ? (
        <canvas ref={canvasRef} className="w-full h-full block cursor-grab active:cursor-grabbing" />
      ) : (
        <div className="w-full h-full flex flex-col items-center justify-center relative bg-gradient-to-b from-[#263845] to-[#152028] p-8 text-[#FFF8F5]">
          <div className="w-48 h-48 rounded-full bg-gradient-to-tr from-[#38607A] via-[#69577E] to-[#7E4F50] blur-xl opacity-60 animate-pulse mb-4" />
          <span className="font-extrabold text-2xl tracking-tight mb-2">POLY Intelligence Engine</span>
          <span className="text-xs text-[#BFC9D0] uppercase tracking-wider font-semibold">Real-Time Multilingual Voice AI</span>
        </div>
      )}

      {/* Storytelling Indicator Overlay (Listen -> Understand -> Confirm -> Escalate) */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-[#FFF8F5]/90 backdrop-blur-md px-4 py-1.5 rounded-full border border-[#BFC9D0]/50 shadow-xs text-[11px] font-bold text-[#263845]">
        <span className={`px-2 py-0.5 rounded-md transition-colors ${activeStep === 'LISTEN' ? 'bg-[#38607A] text-[#FFF8F5]' : 'text-[#263845]/60'}`}>
          01 LISTEN
        </span>
        <span className="text-[#BFC9D0]">→</span>
        <span className={`px-2 py-0.5 rounded-md transition-colors ${activeStep === 'UNDERSTAND' ? 'bg-[#69577E] text-[#FFF8F5]' : 'text-[#263845]/60'}`}>
          02 UNDERSTAND
        </span>
        <span className="text-[#BFC9D0]">→</span>
        <span className={`px-2 py-0.5 rounded-md transition-colors ${activeStep === 'CONFIRM' ? 'bg-[#38607A] text-[#FFF8F5]' : 'text-[#263845]/60'}`}>
          03 CONFIRM
        </span>
        <span className="text-[#BFC9D0]">→</span>
        <span className={`px-2 py-0.5 rounded-md transition-colors ${activeStep === 'ESCALATE' ? 'bg-[#7E4F50] text-[#FFF8F5]' : 'text-[#263845]/60'}`}>
          04 ESCALATE
        </span>
      </div>

    </div>
  );
};

