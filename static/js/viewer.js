import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';

export function initViewer(containerId, fileUrl, fileExt) {
    const container = document.getElementById(containerId);
    const loadingOverlay = document.getElementById('loading-overlay');

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf0f0f0);

    // Camera setup
    let camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
    camera.position.z = 5;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true }); // preserveDrawingBuffer required for screenshots
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    // Lights
    const ambientLight = new THREE.AmbientLight(0x404040);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(1, 1, 1);
    scene.add(directionalLight);
    
    const directionalLight2 = new THREE.DirectionalLight(0xffffff, 0.5);
    directionalLight2.position.set(-1, -1, 1);
    scene.add(directionalLight2);

    let currentMesh = null;

    // Handle Window Resize
    window.addEventListener('resize', () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
    });

    // Load Model
    if (fileExt === 'stl') {
        const loader = new STLLoader();
        loader.load(
            fileUrl,
            function (geometry) {
                const material = new THREE.MeshPhongMaterial({ 
                    color: 0x0055ff, 
                    specular: 0x111111, 
                    shininess: 200,
                    transparent: true,
                    opacity: 1.0
                });
                const mesh = new THREE.Mesh(geometry, material);
                currentMesh = mesh;
                
                // Center geometry
                geometry.center();
                
                // Auto-scale to fit view
                geometry.computeBoundingBox();
                const boundingBox = geometry.boundingBox;
                const size = new THREE.Vector3();
                boundingBox.getSize(size);
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 3 / maxDim;
                mesh.scale.set(scale, scale, scale);

                scene.add(mesh);
                loadingOverlay.style.display = 'none';
            },
            function (xhr) {
                console.log((xhr.loaded / xhr.total * 100) + '% loaded');
            },
            function (error) {
                console.error('An error occurred loading the STL', error);
                loadingOverlay.innerHTML = '<div class="text-danger">Error loading model</div>';
            }
        );
    } else {
        loadingOverlay.innerHTML = '<div class="text-warning">Format not supported for 3D viewing</div>';
    }

    // Animation Loop
    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }

    animate();

    // API for external control
    return {
        setColor: (colorHex) => {
            if (currentMesh) {
                currentMesh.material.color.set(colorHex);
            }
        },
        setOpacity: (opacity) => {
            if (currentMesh) {
                currentMesh.material.opacity = parseFloat(opacity);
                // Need to set transparent to true if opacity < 1, but we set it to true by default
                // currentMesh.material.transparent = opacity < 1.0; 
            }
        },
        setWireframe: (enabled) => {
            if (currentMesh) {
                currentMesh.material.wireframe = enabled;
            }
        },
        setView: (view) => {
            const dist = camera.position.length();
            switch(view) {
                case 'top': camera.position.set(0, dist, 0); break;
                case 'bottom': camera.position.set(0, -dist, 0); break;
                case 'front': camera.position.set(0, 0, dist); break;
                case 'back': camera.position.set(0, 0, -dist); break;
                case 'left': camera.position.set(-dist, 0, 0); break;
                case 'right': camera.position.set(dist, 0, 0); break;
                case 'iso': camera.position.set(dist/Math.sqrt(3), dist/Math.sqrt(3), dist/Math.sqrt(3)); break;
            }
            camera.lookAt(0, 0, 0);
            controls.update();
        },
        getScreenshot: () => {
            renderer.render(scene, camera); // Force a render
            return renderer.domElement.toDataURL('image/png');
        }
    };
}
