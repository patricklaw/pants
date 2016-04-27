

def shards = [:]

def ci = "./build-support/bin/ci.sh"

for (os in ["linux", "osx"]) {

  shards["${os}_self-checks"] = {
    node(os) {
      checkout scm
      sh "${ci} -cjlpn"
    }
  }

  shards["${os}_contrib"] = {
    node(os) {
      checkout scm
      sh "${ci} -fkmsrcjlp"
    }
  }

  (0..9).each { n ->
    def one_indexed = i + 1
    shards["${os}_unit_tests_${one_indexed}_of_10"] = {
      node(os) {
        checkout scm
        sh "${ci} -fkmsrcn -u ${i}/10"
      }
    }
    shards["${os}_integration_tests_${one_indexed}_of_10"] = {
      node(os) {
        checkout scm
        sh "${ci} -fkmsrjlpn -i ${i}/10"
      }
    }
  }
}

parallel shards
