{
  description = "Simple Flask server dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python312;
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            (python.withPackages (ps: with ps; [
              flask
              pip
            ]))
          ];

          shellHook = ''
            echo "Flask dev environment ready"
            echo "Run: python app.py"
          '';
        };
      }
    );
}